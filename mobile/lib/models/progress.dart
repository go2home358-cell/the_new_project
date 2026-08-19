class ProgressSummary {
  ProgressSummary({
    required this.questionsAttempted,
    required this.questionsCorrect,
    required this.accuracy,
    required this.testsCompleted,
    required this.averageScore,
    required this.studySeconds,
    required this.streakCount,
    required this.xp,
    required this.level,
  });

  factory ProgressSummary.fromJson(Map<String, dynamic> json) => ProgressSummary(
        questionsAttempted: json['questions_attempted'] as int,
        questionsCorrect: json['questions_correct'] as int,
        accuracy: (json['accuracy'] as num).toDouble(),
        testsCompleted: json['tests_completed'] as int,
        averageScore: (json['average_score'] as num).toDouble(),
        studySeconds: json['study_seconds'] as int,
        streakCount: json['streak_count'] as int,
        xp: json['xp'] as int,
        level: json['level'] as int,
      );

  final int questionsAttempted;
  final int questionsCorrect;
  final double accuracy;
  final int testsCompleted;
  final double averageScore;
  final int studySeconds;
  final int streakCount;
  final int xp;
  final int level;
}

class ScopePerformance {
  ScopePerformance({
    required this.name,
    required this.attempted,
    required this.correct,
    required this.accuracy,
    required this.completionPercent,
    this.id,
  });

  factory ScopePerformance.fromJson(Map<String, dynamic> json) => ScopePerformance(
        id: json['id'] as int?,
        name: json['name'] as String,
        attempted: json['attempted'] as int,
        correct: json['correct'] as int,
        accuracy: (json['accuracy'] as num).toDouble(),
        completionPercent: (json['completion_percent'] as num? ?? 0).toDouble(),
      );

  final int? id;
  final String name;
  final int attempted;
  final int correct;
  final double accuracy;
  final double completionPercent;
}

class ContinueLearning {
  ContinueLearning({
    required this.subjectId,
    required this.subjectName,
    required this.chapterId,
    required this.chapterName,
    required this.completionPercent,
  });

  factory ContinueLearning.fromJson(Map<String, dynamic> json) => ContinueLearning(
        subjectId: json['subject_id'] as int,
        subjectName: json['subject_name'] as String,
        chapterId: json['chapter_id'] as int,
        chapterName: json['chapter_name'] as String,
        completionPercent: (json['completion_percent'] as num? ?? 0).toDouble(),
      );

  final int subjectId;
  final String subjectName;
  final int chapterId;
  final String chapterName;
  final double completionPercent;
}

class Dashboard {
  Dashboard({
    required this.userName,
    required this.summary,
    required this.subjects,
    required this.dailyChallengeQuestions,
    this.continueLearning,
    this.dailyChallengeTestId,
  });

  factory Dashboard.fromJson(Map<String, dynamic> json) => Dashboard(
        userName: json['user_name'] as String,
        summary: ProgressSummary.fromJson(json['summary'] as Map<String, dynamic>),
        continueLearning: json['continue_learning'] == null
            ? null
            : ContinueLearning.fromJson(json['continue_learning'] as Map<String, dynamic>),
        subjects: ((json['subjects'] as List<dynamic>?) ?? [])
            .map((item) => ScopePerformance.fromJson(item as Map<String, dynamic>))
            .toList(),
        dailyChallengeTestId: json['daily_challenge_test_id'] as int?,
        dailyChallengeQuestions: json['daily_challenge_questions'] as int? ?? 0,
      );

  final String userName;
  final ProgressSummary summary;
  final ContinueLearning? continueLearning;
  final List<ScopePerformance> subjects;
  final int? dailyChallengeTestId;
  final int dailyChallengeQuestions;
}

class WeakTopic {
  WeakTopic({
    required this.topicId,
    required this.topicName,
    required this.chapterName,
    required this.subjectName,
    required this.attempted,
    required this.correct,
    required this.accuracy,
  });

  factory WeakTopic.fromJson(Map<String, dynamic> json) => WeakTopic(
        topicId: json['topic_id'] as int,
        topicName: json['topic_name'] as String,
        chapterName: json['chapter_name'] as String,
        subjectName: json['subject_name'] as String,
        attempted: json['attempted'] as int,
        correct: json['correct'] as int,
        accuracy: (json['accuracy'] as num).toDouble(),
      );

  final int topicId;
  final String topicName;
  final String chapterName;
  final String subjectName;
  final int attempted;
  final int correct;
  final double accuracy;
}

class AchievementBadge {
  AchievementBadge({
    required this.code,
    required this.title,
    required this.description,
    required this.icon,
    required this.earned,
  });

  factory AchievementBadge.fromJson(Map<String, dynamic> json) => AchievementBadge(
        code: json['code'] as String,
        title: json['title'] as String,
        description: json['description'] as String? ?? '',
        icon: json['icon'] as String? ?? '',
        earned: json['earned'] as bool? ?? false,
      );

  final String code;
  final String title;
  final String description;
  final String icon;
  final bool earned;
}

class Bookmark {
  Bookmark({
    required this.id,
    required this.targetType,
    required this.targetId,
    required this.title,
    required this.subtitle,
  });

  factory Bookmark.fromJson(Map<String, dynamic> json) => Bookmark(
        id: json['id'] as int,
        targetType: json['target_type'] as String,
        targetId: json['target_id'] as int,
        title: json['title'] as String,
        subtitle: json['subtitle'] as String? ?? '',
      );

  final int id;
  final String targetType;
  final int targetId;
  final String title;
  final String subtitle;
}

class AiAnswer {
  AiAnswer({required this.answer, required this.source, required this.confident});

  factory AiAnswer.fromJson(Map<String, dynamic> json) => AiAnswer(
        answer: json['answer'] as String,
        source: json['source'] as String,
        confident: json['confident'] as bool? ?? false,
      );

  final String answer;
  final String source;
  final bool confident;

  bool get isUnavailable => source == 'unavailable';
}
