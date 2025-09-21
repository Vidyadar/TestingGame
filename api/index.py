import os
import json
import logging
from flask import Flask, request, jsonify, render_template_string, send_file
from PIL import Image, ImageDraw, ImageFont
import random
from farcaster import validate_message

# Set up logging for better debugging on Vercel
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# In-memory game states, keyed by FID. For a production app, use a database or Redis.
game_states = {}

# Game Constants
GRID_SIZE = 15
CELL_SIZE = 32
IMAGE_SIZE = GRID_SIZE * CELL_SIZE
FONT_PATH = os.path.join(os.path.dirname(__file__), "PressStart2P-Regular.ttf")

# --- Image Generation ---
def draw_game_state(state):
    """Draws the game board, snake, and food onto an image."""
    try:
        font = ImageFont.truetype(FONT_PATH, 16)
    except IOError:
        logging.warning("Font file not found. Using default font.")
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

    if (direction == 'up' and state['direction'] == 'down') or \
       (direction == 'down' and state['direction'] == 'up') or \
       (direction == 'left' and state['direction'] == 'right') or \
       (direction == 'right' and state['direction'] == 'left'):
        direction = state['direction']

    state['direction'] = direction
    new_head = list(head)
    
    if direction == 'up': new_head[1] -= 1
    elif direction == 'down': new_head[1] += 1
    elif direction == 'left': new_head[0] -= 1
    elif direction == 'right': new_head[0] += 1
    
    new_head = tuple(new_head)
    
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
        
        # Ensure the 'static' directory exists before saving the image
        static_dir = os.path.join(app.root_path, "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
            
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
            body = request.get_data()
            logging.info(f"Received request body: {body}")
            
            # Validate the Farcaster request using the dedicated function
            frame_data = validate_message(body)
            user_fid = frame_data.fid
            
            action = frame_data.button_index
            
            if action == 1 and user_fid not in game_states:
                game_states[user_fid] = create_initial_state()
            
            state = game_states.get(user_fid
