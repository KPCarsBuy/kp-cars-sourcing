const express = require('express');
const path = require('node:path');

const app = express();
const port = Number(process.env.PORT) || 3000;

// Version 1: stock saved in this browser; no external listings or API connection.
app.use(express.static(path.join(__dirname, 'public')));
app.get('/api/health', (_req, res) => res.json({ status: 'ok', service: 'KP Cars Stock Manager' }));

app.listen(port, '0.0.0.0', () => console.log(`KP Cars listening on port ${port}`));
