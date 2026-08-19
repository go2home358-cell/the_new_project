import 'package:flutter_test/flutter_test.dart';
import 'package:science_study/core/api_client.dart';
import 'package:science_study/core/token_storage.dart';
import 'package:science_study/data/practice_repository.dart';
import 'package:science_study/state/attempt_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/fake_http_client.dart';

Map<String, dynamic> _question(int id) => {
      'id': id,
      'text': 'Question $id',
      'difficulty': 'easy',
      'subject_id': 1,
      'chapter_id': 1,
      'topic_id': 2,
      'options': [
        {'id': id * 10 + 1, 'label': 'A', 'text': 'first'},
        {'id': id * 10 + 2, 'label': 'B', 'text': 'second'},
      ],
    };

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({'access_token': 'token', 'refresh_token': 'refresh'}));

  (PracticeRepository, FakeHttpClient) build() {
    final http = FakeHttpClient();
    final api = ApiClient(baseUrl: 'http://localhost/api/v1', storage: TokenStorage(), httpClient: http);
    return (PracticeRepository(api), http);
  }

  test('startPractice maps the attempt payload', () async {
    final (practice, http) = build();
    http.stub('POST', '/practice/sessions', 201, {
      'id': 3,
      'mode': 'practice',
      'status': 'in_progress',
      'total': 2,
      'started_at': '2026-01-01T10:00:00Z',
      'duration_seconds': null,
      'questions': [_question(1), _question(2)],
    });

    final attempt = await practice.startPractice(mode: 'random', count: 2);

    expect(attempt.id, 3);
    expect(attempt.isTimed, isFalse);
    expect(attempt.questions.length, 2);
  });

  test('practice answers reveal feedback and lock the question', () async {
    final (practice, http) = build();
    http.stub('POST', '/practice/sessions', 201, {
      'id': 3,
      'mode': 'practice',
      'status': 'in_progress',
      'total': 2,
      'started_at': '2026-01-01T10:00:00Z',
      'questions': [_question(1), _question(2)],
    });
    http.stub('POST', '/attempts/3/answers', 200, {
      'question_id': 1,
      'is_correct': true,
      'correct_option_id': 11,
      'correct_option_label': 'A',
      'explanation': 'A is right.',
    });

    final attempt = await practice.startPractice(mode: 'random', count: 2);
    final controller = AttemptController(practice, attempt);

    await controller.select(11);

    expect(controller.currentFeedback!.isCorrect, isTrue);
    expect(controller.answeredCount, 1);

    // A revealed practice question ignores further taps.
    await controller.select(12);
    expect(controller.selectedOptions[1], 11);

    controller.next();
    expect(controller.index, 1);
    expect(controller.currentFeedback, isNull);
    controller.dispose();
  });

  test('timed attempts hide the answer and expose a countdown', () async {
    final (practice, http) = build();
    final startedAt = DateTime.now().toUtc().subtract(const Duration(seconds: 30));
    http.stub('POST', '/tests/9/start', 201, {
      'id': 4,
      'mode': 'mock',
      'status': 'in_progress',
      'total': 1,
      'started_at': startedAt.toIso8601String(),
      'duration_seconds': 300,
      'questions': [_question(1)],
    });
    http.stub('POST', '/attempts/4/answers', 200, {'question_id': 1});
    http.stub('POST', '/attempts/4/submit', 200, {
      'attempt_id': 4,
      'mode': 'mock',
      'total': 1,
      'attempted': 1,
      'correct': 1,
      'incorrect': 0,
      'unattempted': 0,
      'accuracy': 100.0,
      'score': 100.0,
      'time_used_seconds': 35,
    });

    final attempt = await practice.startTest(9);
    final controller = AttemptController(practice, attempt);

    expect(attempt.isTimed, isTrue);
    expect(controller.remainingSeconds, lessThanOrEqualTo(270));

    await controller.select(11);
    expect(controller.currentFeedback!.revealsAnswer, isFalse);

    final result = await controller.submit();
    expect(result!.score, 100.0);
    controller.dispose();
  });

  test('mark for review toggles and is reported to the backend', () async {
    final (practice, http) = build();
    http.stub('POST', '/practice/sessions', 201, {
      'id': 5,
      'mode': 'practice',
      'status': 'in_progress',
      'total': 1,
      'started_at': '2026-01-01T10:00:00Z',
      'questions': [_question(1)],
    });
    http.stub('POST', '/attempts/5/answers', 200, {'question_id': 1});

    final attempt = await practice.startPractice(mode: 'random', count: 1);
    final controller = AttemptController(practice, attempt);

    await controller.toggleMarkForReview();
    expect(controller.markedCount, 1);

    await controller.toggleMarkForReview();
    expect(controller.markedCount, 0);
    expect(http.requests.where((entry) => entry == 'POST /attempts/5/answers').length, 2);
    controller.dispose();
  });
}
