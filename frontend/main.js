
console.log("DancePlanet frontpage loaded");

document.addEventListener("mousemove", (e) => {
  const stars = document.querySelector(".bg-stars");
  if (!stars) return;
  stars.style.transform = `translate(${e.clientX * 0.01}px, ${e.clientY * 0.01}px)`;
});
