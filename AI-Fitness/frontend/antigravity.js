/**
 * Pure function to calculate Anti-Gravity score.
 * Returns 0 if the user hasn't logged any exercises, ensuring predictable UI state.
 */
function getAntiGravityScore(workouts = []) {
  // 1. Guard clause for empty or null states
  if (!Array.isArray(workouts) || workouts.length === 0) {
    return 0;
  }

  // 2. Pure reduction with safe fallbacks for missing properties
  const totalScore = workouts.reduce((acc, session) => {
    // Supports both 'reps' and FitQuest 'repetitions', and 'timeUnderTension' or 'duration_sec'
    const reps = session.reps !== undefined ? session.reps : (session.repetitions || 0);
    const timeUnderTension = session.timeUnderTension !== undefined ? session.timeUnderTension : (session.duration_sec || 0); 
    const resistance = session.weight || session.bodyweightFactor || (session.bodyweight_factor || 1);

    // Prevent division by zero or multiplying by corrupted negative data
    if (reps <= 0 || timeUnderTension <= 0) {
      return acc;
    }

    // Anti-Gravity metric logic (Work / Time)
    const sessionScore = (reps * resistance) / timeUnderTension;
    return acc + sessionScore;
  }, 0);

  // 3. Return a clean, rounded number
  return Number(totalScore.toFixed(2));
}

// Universal Browser Global & CommonJS Export Compatibility
if (typeof window !== 'undefined') {
  window.getAntiGravityScore = getAntiGravityScore;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { getAntiGravityScore };
}
