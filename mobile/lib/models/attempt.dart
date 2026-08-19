import 'question.dart';

class Attempt {
  Attempt({
    required this.id,
    required this.mode,
    required this.status,
    required this.startedAt,
    required this.total,
    required this.questions,
    this.durationSeconds,
    this.testId,
    this.title = '',
  });

  factory Attempt.fromJson(Map<String, dynamic> json) => Attempt(
        id: json['id'] as int,
        mode: json['mode'] as String,
        status: json['status'] as String,
        startedAt: DateTime.parse(json['started_at'] as String),
        durationSeconds: json['duration_seconds'] as int?,
        total: json['total'] as int,
        testId: json['test_id'] as int?,
        title: json['title'] as String? ?? '',
        questions: ((json['questions'] as List<dynamic>?) ?? [])
            .map((item) => Question.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  final int id;
  final String mode;
  final String status;
  final DateTime startedAt;
  final int? durationSeconds;
  final int total;
  final int? testId;
  final String title;
  final List<Question> questions;

  bool get isTimed => durationSeconds != null;
}

class AnswerFeedback {
  AnswerFeedback({
    required this.questionId,
    required this.markedForReview,
    this.isCorrect,
    this.correctOptionId,
    this.correctOptionLabel,
    this.explanation = '',
  });

  factory AnswerFeedback.fromJson(Map<String, dynamic> json) => AnswerFeedback(
        questionId: json['question_id'] as int,
        isCorrect: json['is_correct'] as bool?,
        correctOptionId: json['correct_option_id'] as int?,
        correctOptionLabel: json['correct_option_label'] as String?,
        explanation: json['explanation'] as String? ?? '',
        markedForReview: json['marked_for_review'] as bool? ?? false,
      );

  final int questionId;
  final bool? isCorrect;
  final int? correctOptionId;
  final String? correctOptionLabel;
  final String explanation;
  final bool markedForReview;

  bool get revealsAnswer => correctOptionId != null;
}

class TopicPerformance {
  TopicPerformance({
    required this.topicName,
    required this.total,
    required this.correct,
    required this.accuracy,
    this.topicId,
  });

  factory TopicPerformance.fromJson(Map<String, dynamic> json) => TopicPerformance(
        topicId: json['topic_id'] as int?,
        topicName: json['topic_name'] as String,
        total: json['total'] as int,
        correct: json['correct'] as int,
        accuracy: (json['accuracy'] as num).toDouble(),
      );

  final int? topicId;
  final String topicName;
  final int total;
  final int correct;
  final double accuracy;
}

class AttemptResult {
  AttemptResult({
    required this.attemptId,
    required this.mode,
    required this.total,
    required this.attempted,
    required this.correct,
    required this.incorrect,
    required this.unattempted,
    required this.accuracy,
    required this.score,
    required this.timeUsedSeconds,
    required this.xpEarned,
    required this.newBadges,
    required this.topicPerformance,
    required this.weakTopics,
    this.durationSeconds,
  });

  factory AttemptResult.fromJson(Map<String, dynamic> json) => AttemptResult(
        attemptId: json['attempt_id'] as int,
        mode: json['mode'] as String,
        total: json['total'] as int,
        attempted: json['attempted'] as int,
        correct: json['correct'] as int,
        incorrect: json['incorrect'] as int,
        unattempted: json['unattempted'] as int,
        accuracy: (json['accuracy'] as num).toDouble(),
        score: (json['score'] as num).toDouble(),
        timeUsedSeconds: json['time_used_seconds'] as int? ?? 0,
        durationSeconds: json['duration_seconds'] as int?,
        xpEarned: json['xp_earned'] as int? ?? 0,
        newBadges: ((json['new_badges'] as List<dynamic>?) ?? []).map((item) => '$item').toList(),
        topicPerformance: ((json['topic_performance'] as List<dynamic>?) ?? [])
            .map((item) => TopicPerformance.fromJson(item as Map<String, dynamic>))
            .toList(),
        weakTopics: ((json['weak_topics'] as List<dynamic>?) ?? []).map((item) => '$item').toList(),
      );

  final int attemptId;
  final String mode;
  final int total;
  final int attempted;
  final int correct;
  final int incorrect;
  final int unattempted;
  final double accuracy;
  final double score;
  final int timeUsedSeconds;
  final int? durationSeconds;
  final int xpEarned;
  final List<String> newBadges;
  final List<TopicPerformance> topicPerformance;
  final List<String> weakTopics;
}

class ReviewItem {
  ReviewItem({
    required this.question,
    required this.explanation,
    this.selectedOptionId,
    this.correctOptionId,
    this.isCorrect,
  });

  factory ReviewItem.fromJson(Map<String, dynamic> json) => ReviewItem(
        question: Question.fromJson(json['question'] as Map<String, dynamic>),
        selectedOptionId: json['selected_option_id'] as int?,
        correctOptionId: json['correct_option_id'] as int?,
        isCorrect: json['is_correct'] as bool?,
        explanation: json['explanation'] as String? ?? '',
      );

  final Question question;
  final int? selectedOptionId;
  final int? correctOptionId;
  final bool? isCorrect;
  final String explanation;
}

class MockTest {
  MockTest({
    required this.id,
    required this.title,
    required this.kind,
    required this.durationSeconds,
    required this.totalQuestions,
    this.subjectId,
    this.difficulty,
  });

  factory MockTest.fromJson(Map<String, dynamic> json) => MockTest(
        id: json['id'] as int,
        title: json['title'] as String,
        kind: json['kind'] as String,
        durationSeconds: json['duration_seconds'] as int,
        totalQuestions: json['total_questions'] as int,
        subjectId: json['subject_id'] as int?,
        difficulty: json['difficulty'] as String?,
      );

  final int id;
  final String title;
  final String kind;
  final int durationSeconds;
  final int totalQuestions;
  final int? subjectId;
  final String? difficulty;
}
