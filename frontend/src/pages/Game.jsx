
import { useEffect } from "react";

export default function Game() {
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "/game/game.bundle.js";
    script.type = "module";
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  return (
    <div style={{ width: "100vw", height: "100vh", overflow: "hidden" }}>
      <canvas id="game-canvas"></canvas>
    </div>
  );
}
