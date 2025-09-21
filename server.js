const express = require('express');
const cors = require('cors');
const app = express();
const port = 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// This route serves the initial Farcaster Frame HTML.
// When a user sees your post, the Farcaster app requests this URL.
app.get('/frame', (req, res) => {
    // The meta tags in frame.html tell Farcaster how to display the frame and what button actions to take.
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <meta property="fc:frame" content="vNext" />
            <meta property="fc:frame:image" content="https://placehold.co/600x400/000000/00ff00?text=Retro+Snake+Game" />
            <meta property="fc:frame:button:1" content="Start Game" />
            <meta property="fc:frame:button:1:action" content="link" />
            <meta property="fc:frame:button:1:target" content="YOUR_GAME_URL_HERE" />
            <meta property="fc:frame:post_url" content="YOUR_SERVER_URL_HERE/frame" />
        </head>
        <body>
            <h1>Retro Snake Game</h1>
        </body>
        </html>
    `);
});

// This route handles the placeholder NFT minting process.
// Your game's JavaScript will send a request to this endpoint.
app.post('/mint-nft', (req, res) => {
    const { userId, score } = req.body;
    
    // In a real application, you would add logic here to:
    // 1. Validate the request (e.g., check if the user is authenticated).
    // 2. Interact with a blockchain smart contract to mint an NFT.
    // 3. The minting process is complex and requires a separate smart contract.
    // This is a simple placeholder to demonstrate the flow.

    console.log(`Received request to mint NFT for User: ${userId} with Score: ${score}`);
    
    // A successful response to the frontend.
