class QuestionOption {
  QuestionOption({required this.id, required this.label, required this.text});

  factory QuestionOption.fromJson(Map<String, dynamic> json) => QuestionOption(
        id: json['id'] as int,
        label: json['label'] as String,
        text: json['text'] as String,
      );

  final int id;
  final String label;
  final String text;
}

class Question {
  Question({
    required this.id,
    required this.text,
    required this.difficulty,
    required this.subjectId,
    required this.chapterId,
    required this.options,
    required this.isBookmarked,
    this.topicId,
    this.source = '',
    this.year,
    this.imageUrl,
  });

  factory Question.fromJson(Map<String, dynamic> json) => Question(
        id: json['id'] as int,
        text: json['text'] as String,
        difficulty: json['difficulty'] as String? ?? 'medium',
        subjectId: json['subject_id'] as int,
        chapterId: json['chapter_id'] as int,
        topicId: json['topic_id'] as int?,
        source: json['source'] as String? ?? '',
        year: json['year'] as int?,
        imageUrl: json['image_url'] as String?,
        options: ((json['options'] as List<dynamic>?) ?? [])
            .map((item) => QuestionOption.fromJson(item as Map<String, dynamic>))
            .toList(),
        isBookmarked: json['is_bookmarked'] as bool? ?? false,
      );

  final int id;
  final String text;
  final String difficulty;
  final int subjectId;
  final int chapterId;
  final int? topicId;
  final String source;
  final int? year;
  final String? imageUrl;
  final List<QuestionOption> options;
  final bool isBookmarked;
}
