import express from 'express';
import cors from 'cors';
const app = express();
app.use(cors());
app.use(express.json());
let leaderboard = [{ name: "NinjaNova", score: 1240 }, { name: "ShadowKick", score: 1180 }];
app.get('/api/leaderboard', (req, res) => {
    res.json(leaderboard);
});
app.post('/api/match-result', (req, res) => {
    const { name, score } = req.body;
    leaderboard.push({ name, score });
    leaderboard = leaderboard.sort((a,b) => b.score - a.score).slice(0, 50);
    res.json({ ok: true });
});
app.listen(4000, () => console.log("DancePlanet API körs på port 4000"));