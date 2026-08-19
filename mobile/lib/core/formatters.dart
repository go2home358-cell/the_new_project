String formatDuration(int seconds) {
  final clamped = seconds < 0 ? 0 : seconds;
  final hours = clamped ~/ 3600;
  final minutes = (clamped % 3600) ~/ 60;
  final secs = clamped % 60;
  final mm = minutes.toString().padLeft(2, '0');
  final ss = secs.toString().padLeft(2, '0');
  return hours > 0 ? '$hours:$mm:$ss' : '$mm:$ss';
}

String formatStudyTime(int seconds) {
  if (seconds < 60) return '${seconds}s';
  final hours = seconds ~/ 3600;
  final minutes = (seconds % 3600) ~/ 60;
  if (hours == 0) return '${minutes}m';
  return '${hours}h ${minutes}m';
}

String formatPercent(num value) => '${value.toStringAsFixed(value % 1 == 0 ? 0 : 1)}%';
