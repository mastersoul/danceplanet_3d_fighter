
import express from "express";
import cors from "cors";
import { createServer } from "http";
import { Server } from "socket.io";

const app = express();
app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("DancePlanet backend running");
});

const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: "*" } });

io.on("connection", socket => {
  console.log("User connected:", socket.id);
});

const PORT = process.env.PORT || 4000;
httpServer.listen(PORT, () => console.log("Backend running on port", PORT));
