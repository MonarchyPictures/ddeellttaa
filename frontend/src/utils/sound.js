// Simple "pop" sound as base64
const POP_SOUND = 'data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU'; // Truncated for brevity, I should use a real one or just a placeholder function that logs if I can't easily generate one.

// Actually, I'll use a slightly longer one or generate a beep using AudioContext if possible, but AudioContext is better.
// Let's use AudioContext for a simple beep/notification sound.

export const playNotificationSound = () => {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;

    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime); // A5
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.1); // Drop to A4

    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);

    osc.start();
    osc.stop(ctx.currentTime + 0.1);
  } catch (e) {
    console.error('Audio play failed', e);
  }
};
