import 'package:flutter_test/flutter_test.dart';
import 'package:science_study/core/formatters.dart';

void main() {
  test('formatDuration renders mm:ss and h:mm:ss', () {
    expect(formatDuration(0), '00:00');
    expect(formatDuration(65), '01:05');
    expect(formatDuration(3725), '1:02:05');
  });

  test('formatStudyTime is human readable', () {
    expect(formatStudyTime(0), '0s');
    expect(formatStudyTime(600), '10m');
    expect(formatStudyTime(5400), '1h 30m');
  });

  test('formatPercent trims trailing zeros', () {
    expect(formatPercent(0), '0%');
    expect(formatPercent(66.67), '66.7%');
    expect(formatPercent(100), '100%');
  });
}
