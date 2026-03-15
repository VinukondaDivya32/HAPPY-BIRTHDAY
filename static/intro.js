document.addEventListener('DOMContentLoaded', () => {
  const introScreen = document.querySelector('.intro-screen');
  const balloonContainer = document.querySelector('.balloon-container');
  const sparkleContainer = document.querySelector('.sparkle-container');

  if (!introScreen || !balloonContainer || !sparkleContainer) {
    console.error('Intro elements not found!');
    return;
  }

  const particleCount = {
    balloons: 60,
    sparkles: 40,
  };

  const colors = ['#ff7979', '#badc58', '#f9ca24', '#f0932b', '#eb4d4b', '#6ab04c', '#7ed6df'];

  // --- Balloon Splash from Center ---
  function createBalloonSplash() {
    for (let i = 0; i < particleCount.balloons; i++) {
      const balloon = document.createElement('div');
      balloon.className = 'balloon';

      const size = Math.random() * 20 + 10; // Size between 10px and 30px
      balloon.style.width = `${size}px`;
      balloon.style.height = `${size * 1.2}px`;
      balloon.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];

      // Animation properties
      const angle = Math.random() * 360; // Random direction
      const distance = Math.random() * 300 + 250; // Travel distance
      const duration = Math.random() * 3 + 5; // 5s to 8s

      const tx = Math.cos(angle * Math.PI / 180) * distance;
      const ty = Math.sin(angle * Math.PI / 180) * distance;

      balloon.animate([
        { transform: 'translate(0, 0) scale(0)', opacity: 1 },
        { transform: `translate(${tx}px, ${ty}px) scale(1)`, opacity: 0 }
      ], {
        duration: duration * 1000,
        easing: 'cubic-bezier(0.1, 0.9, 0.2, 1)',
        fill: 'forwards'
      });

      balloonContainer.appendChild(balloon);
      // Clean up the DOM after animation
      setTimeout(() => balloon.remove(), duration * 1000);
    }
  }

  // --- Shining Sparkle Dots ---
  function createSparkles() {
    for (let i = 0; i < particleCount.sparkles; i++) {
      const sparkle = document.createElement('div');
      sparkle.className = 'sparkle';

      const size = Math.random() * 8 + 2; // 2px to 10px
      sparkle.style.width = `${size}px`;
      sparkle.style.height = `${size}px`;
      sparkle.style.top = `${Math.random() * 100}%`;
      sparkle.style.left = `${Math.random() * 100}%`;

      const duration = Math.random() * 2 + 1.5; // 1.5s to 3.5s
      const delay = Math.random() * 3;

      sparkle.animate([
        { transform: 'scale(0)', opacity: 0 },
        { transform: 'scale(1)', opacity: 1 },
        { transform: 'scale(0)', opacity: 0 }
      ], {
        duration: duration * 1000,
        delay: delay * 1000,
        easing: 'ease-in-out',
        iterations: Infinity
      });

      sparkleContainer.appendChild(sparkle);
    }
  }

  // --- Tap to Enter Logic ---
  function setupEnterInteraction() {
    introScreen.addEventListener('click', () => {
      // 1. Fade out the intro screen
      introScreen.classList.add('fade-away');

      // 2. Inform the server that the greeting has been seen
      fetch('/set_greeted', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ greeted: true })
      }).catch(err => console.error('Failed to set greeted status:', err));

      // 3. Remove the intro from the DOM after the transition
      setTimeout(() => {
        introScreen.remove();
      }, 700); // Matches the CSS transition duration
    }, { once: true }); // Only allow the event to fire once
  }

  // --- Initialize ---
  createBalloonSplash();
  createSparkles();
  setupEnterInteraction();
});
