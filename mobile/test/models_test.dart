import 'package:flutter_test/flutter_test.dart';
import 'package:science_study/models/attempt.dart';
import 'package:science_study/models/content.dart';
import 'package:science_study/models/progress.dart';
import 'package:science_study/models/question.dart';
import 'package:science_study/models/user.dart';

void main() {
  test('AppUser parses roles and gamification fields', () {
    final user = AppUser.fromJson({
      'id': 7,
      'name': 'Sandesh',
      'email': 'sandesh@example.com',
      'role': 'admin',
      'xp': 120,
      'level': 2,
      'streak_count': 4,
    });

    expect(user.id, 7);
    expect(user.isAdmin, isTrue);
    expect(user.level, 2);
    expect(user.streakCount, 4);
  });

  test('Question keeps options ordered and never carries the answer', () {
    final question = Question.fromJson({
      'id': 11,
      'text': 'What is the SI unit of force?',
      'difficulty': 'easy',
      'subject_id': 1,
      'chapter_id': 2,
      'topic_id': 3,
      'is_bookmarked': true,
      'options': [
        {'id': 1, 'label': 'A', 'text': 'newton'},
        {'id': 2, 'label': 'B', 'text': 'joule'},
      ],
    });

    expect(question.options.map((option) => option.label), ['A', 'B']);
    expect(question.isBookmarked, isTrue);
  });

  test('Attempt detects timed tests', () {
    final base = {
      'id': 4,
      'mode': 'mock',
      'status': 'in_progress',
      'total': 1,
      'started_at': '2026-01-01T10:00:00Z',
      'questions': <Map<String, dynamic>>[
        {
          'id': 9,
          'text': 'Q',
          'difficulty': 'medium',
          'subject_id': 1,
          'chapter_id': 1,
          'options': [
            {'id': 1, 'label': 'A', 'text': 'x'},
          ],
        },
      ],
    };

    expect(Attempt.fromJson({...base, 'duration_seconds': 600}).isTimed, isTrue);
    expect(Attempt.fromJson({...base, 'duration_seconds': null}).isTimed, isFalse);
  });

  test('AnswerFeedback only reveals the answer when the backend sends one', () {
    final hidden = AnswerFeedback.fromJson({'question_id': 9});
    final revealed = AnswerFeedback.fromJson({
      'question_id': 9,
      'is_correct': false,
      'correct_option_id': 2,
      'correct_option_label': 'B',
      'explanation': 'Because force equals mass times acceleration.',
    });

    expect(hidden.revealsAnswer, isFalse);
    expect(revealed.revealsAnswer, isTrue);
    expect(revealed.correctOptionLabel, 'B');
  });

  test('AttemptResult parses totals and topic performance', () {
    final result = AttemptResult.fromJson({
      'attempt_id': 5,
      'mode': 'practice',
      'total': 4,
      'attempted': 3,
      'correct': 2,
      'incorrect': 1,
      'unattempted': 1,
      'accuracy': 66.67,
      'score': 50.0,
      'time_used_seconds': 90,
      'xp_earned': 20,
      'new_badges': ['First steps'],
      'weak_topics': ['Kinematics'],
      'topic_performance': [
        {'topic_id': 3, 'topic_name': 'Kinematics', 'total': 2, 'correct': 1, 'accuracy': 50.0},
      ],
    });

    expect(result.accuracy, 66.67);
    expect(result.topicPerformance.single.topicName, 'Kinematics');
    expect(result.newBadges, ['First steps']);
  });

  test('Dashboard and subject payloads map snake_case keys', () {
    final dashboard = Dashboard.fromJson({
      'user_name': 'Sandesh',
      'summary': {
        'questions_attempted': 10,
        'questions_correct': 7,
        'accuracy': 70.0,
        'tests_completed': 1,
        'average_score': 65.0,
        'study_seconds': 3600,
        'streak_count': 3,
        'xp': 200,
        'level': 3,
      },
      'subjects': [
        {'id': 1, 'name': 'Physics', 'attempted': 10, 'correct': 7, 'accuracy': 70.0, 'completion_percent': 25.0},
      ],
      'continue_learning': {
        'subject_id': 1,
        'chapter_id': 2,
        'chapter_name': 'Motion',
        'subject_name': 'Physics',
        'completion_percent': 40.0,
      },
    });

    expect(dashboard.summary.level, 3);
    expect(dashboard.subjects.single.name, 'Physics');
    expect(dashboard.continueLearning!.chapterId, 2);

    final subject = Subject.fromJson({
      'id': 1,
      'name': 'Physics',
      'description': 'Mechanics and more',
      'chapter_count': 8,
      'question_count': 40,
      'completion_percent': 12.5,
    });
    expect(subject.chapterCount, 8);
    expect(subject.completionPercent, 12.5);
  });

  test('AiAnswer flags the unavailable fallback', () {
    expect(AiAnswer.fromJson({'answer': 'x', 'source': 'unavailable'}).isUnavailable, isTrue);
    expect(AiAnswer.fromJson({'answer': 'x', 'source': 'stored_material'}).isUnavailable, isFalse);
  });
}
