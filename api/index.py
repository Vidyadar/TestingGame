import os
import json
from flask import Flask, request, jsonify, render_template_string, send_file
from PIL import Image, ImageDraw, ImageFont
import random
from farcaster.client import Farcaster

# Initialize Flask app
app = Flask(__name__)

# In-memory game states, keyed by FID. For a production app, use a database or Redis.
game_states = {}

# Game Constants
GRID_SIZE = 15
CELL_SIZE = 32
IMAGE_SIZE = GRID_SIZE * CELL_SIZE

# Path to the font file, adjusted for Vercel's file system
FONT_PATH = os.path.join(os.path.dirname(__file__), "PressStart2P-Regular.ttf")

# --- Image Generation ---
def draw_game_state(state):
    """Draws the game board, snake, and food onto an image."""
    try:
        font = ImageFont.truetype(FONT_PATH, 16)
    except IOError:
        font = ImageFont.load_default()

    img = Image.new('RGB', (IMAGE_SIZE, IMAGE_SIZE), color=(25, 25, 25))
    draw = ImageDraw.Draw(img)

    # Draw grid
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            draw.rectangle(
                [x * CELL_SIZE, y * CELL_SIZE, (x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE],
                fill=(40, 40, 40),
                outline=(50, 50, 50)
            )

    # Draw food
    fx, fy = state['food']
    draw.rectangle(
        [fx * CELL_SIZE, fy * CELL_SIZE, (fx + 1) * CELL_SIZE, (fy + 1) * CELL_SIZE],
        fill=(255, 69, 0)
    )

    # Draw snake
    for i, (x, y) in enumerate(state['snake']):
        color = (0, 255, 0) if i == 0 else (144, 238, 144)
        draw.rectangle(
            [x * CELL_SIZE, y * CELL_SIZE, (x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE],
            fill=color
        )

    # Draw score and game over text
    score_text = f"Score: {state['score']}"
    draw.text((10, 10), score_text, fill=(255, 255, 255), font=font)
    if state['game_over']:
        msg = "Game Over"
        bbox = draw.textbbox((0, 0), msg, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text(
            ((IMAGE_SIZE - text_width) / 2, (IMAGE_SIZE - text_height) / 2),
            msg, fill=(255, 0, 0), font=font
        )
    return img

# --- Game Logic ---
def create_initial_state():
    """Initializes a new game state."""
    snake = [(GRID_SIZE // 2, GRID_SIZE // 2)]
    food = generate_food(snake)
    return {
        'snake': snake,
        'food': food,
        'direction': 'right',
        'score': 0,
        'game_over': False
    }

def generate_food(snake):
    """Generates food at a random position not occupied by the snake."""
    while True:
        food_pos = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
        if food_pos not in snake:
            return food_pos

def move_snake(state, direction):
    """Updates the game state based on the user's move."""
    snake = state['snake']
    head = snake[0]

    # Check for opposite direction moves
    if (direction == 'up' and state['direction'] == 'down') or \
       (direction == 'down' and state['direction'] == 'up') or \
       (direction == 'left' and state['direction'] == 'right') or \
       (direction == 'right' and state['direction'] == 'left'):
        direction = state['direction'] # Don't allow reversing direction

    state['direction'] = direction
    new_head = list(head)
    
    # Calculate new head position
    if direction == 'up': new_head[1] -= 1
    elif direction == 'down': new_head[1] += 1
    elif direction == 'left': new_head[0] -= 1
    elif direction == 'right': new_head[0] += 1
    
    new_head = tuple(new_head)
    
    # Check for collisions with walls or self
    if not (0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE) or new_head in snake:
        state['game_over'] = True
        return

    snake.insert(0, new_head)
    if new_head == state['food']:
        state['score'] += 1
        state['food'] = generate_food(snake)
    else:
        snake.pop()

# --- Farcaster Frame Routes ---
@app.route("/", methods=["GET", "POST"])
async def home():
    """Main route to serve the frame or process user actions."""
    if request.method == 'GET':
        initial_state = create_initial_state()
        image = draw_game_state(initial_state)
        image_path = "static/initial_frame.png"
        image.save(os.path.join(app.root_path, image_path))

        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta property="fc:frame" content="vNext" />
            <meta property="fc:frame:image" content="/static/initial_frame.png" />
            <meta property="fc:frame:post_url" content="/" />
            <meta property="fc:frame:button:1" content="Start Game" />
        </head>
        </html>
        """)

    else: # POST request (user interaction)
        try:
            # Validate the Farcaster request
            fc = Farcaster()
            frame_data = await fc.validate_message(request.get_data())
            user_fid = frame_data.fid
            
            # Get the button index clicked
            action = request.get_json()['untrustedData']['buttonIndex']
            
            # Get or create game state
            if user_fid not in game_states or game_states[user_fid]['game_over']:
                game_states[user_fid] = create_initial_state()
            
            state = game_states[user_fid]
            
            # Process move
            direction_map = {1: 'up', 2: 'down', 3: 'left', 4: 'right'}
            if action in direction_map:
                move_snake(state, direction_map[action])

            # Render the updated image
            image = draw_game_state(state)
            image_filename = f"game_frame_{user_fid}.png"
            image_path = os.path.join(app.root_path, "static", image_filename)
            
            # Ensure the static directory exists
            if not os.path.exists(os.path.join(app.root_path, "static")):
                os.makedirs(os.path.join(app.root_path, "static"))
            
            image.save(image_path)
            
            # Determine buttons for the next frame
            if state['game_over']:
                buttons_html = """
                <meta property="fc:frame:button:1" content="Play Again" />
                """
            else:
                buttons_html = """
                <meta property="fc:frame:button:1" content="⬆️" />
                <meta property="fc:frame:button:2" content="⬇️" />
                <meta property="fc:frame:button:3" content="⬅️" />
                <meta property="fc:frame:button:4" content="➡️" />
                """

            return render_template_string(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta property="fc:frame" content="vNext" />
                <meta property="fc:frame:image" content="/static/{image_filename}" />
                <meta property="fc:frame:post_url" content="/" />
                {buttons_html}
            </head>
            </html>
            """)

        except Exception as e:
            # Vercel requires a specific response for errors
            return jsonify({"error": str(e)}), 500

@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files (images) from the 'static' directory."""
    return send_file(os.path.join(app.root_path, "static", filename))
