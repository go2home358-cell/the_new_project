class Subject {
  Subject({
    required this.id,
    required this.name,
    required this.icon,
    required this.color,
    required this.description,
    required this.chapterCount,
    required this.questionCount,
    required this.completionPercent,
  });

  factory Subject.fromJson(Map<String, dynamic> json) => Subject(
        id: json['id'] as int,
        name: json['name'] as String,
        icon: json['icon'] as String? ?? 'science',
        color: json['color'] as String? ?? '#3F51B5',
        description: json['description'] as String? ?? '',
        chapterCount: json['chapter_count'] as int? ?? 0,
        questionCount: json['question_count'] as int? ?? 0,
        completionPercent: (json['completion_percent'] as num? ?? 0).toDouble(),
      );

  final int id;
  final String name;
  final String icon;
  final String color;
  final String description;
  final int chapterCount;
  final int questionCount;
  final double completionPercent;
}

class Chapter {
  Chapter({
    required this.id,
    required this.subjectId,
    required this.name,
    required this.description,
    required this.questionCount,
    required this.completionPercent,
  });

  factory Chapter.fromJson(Map<String, dynamic> json) => Chapter(
        id: json['id'] as int,
        subjectId: json['subject_id'] as int,
        name: json['name'] as String,
        description: json['description'] as String? ?? '',
        questionCount: json['question_count'] as int? ?? 0,
        completionPercent: (json['completion_percent'] as num? ?? 0).toDouble(),
      );

  final int id;
  final int subjectId;
  final String name;
  final String description;
  final int questionCount;
  final double completionPercent;
}

class Topic {
  Topic({required this.id, required this.name, required this.questionCount, this.accuracy});

  factory Topic.fromJson(Map<String, dynamic> json) => Topic(
        id: json['id'] as int,
        name: json['name'] as String,
        questionCount: json['question_count'] as int? ?? 0,
        accuracy: (json['accuracy'] as num?)?.toDouble(),
      );

  final int id;
  final String name;
  final int questionCount;
  final double? accuracy;
}

class Concept {
  Concept({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    required this.isBookmarked,
  });

  factory Concept.fromJson(Map<String, dynamic> json) => Concept(
        id: json['id'] as int,
        kind: json['kind'] as String,
        title: json['title'] as String,
        body: json['body'] as String? ?? '',
        isBookmarked: json['is_bookmarked'] as bool? ?? false,
      );

  final int id;
  final String kind;
  final String title;
  final String body;
  final bool isBookmarked;
}

class ChapterDetail {
  ChapterDetail({
    required this.chapter,
    required this.subjectName,
    required this.topics,
    required this.concepts,
    required this.formulas,
    required this.examples,
    required this.points,
  });

  factory ChapterDetail.fromJson(Map<String, dynamic> json) {
    List<Concept> parse(String key) =>
        ((json[key] as List<dynamic>?) ?? []).map((item) => Concept.fromJson(item as Map<String, dynamic>)).toList();
    return ChapterDetail(
      chapter: Chapter.fromJson(json),
      subjectName: json['subject_name'] as String? ?? '',
      topics: ((json['topics'] as List<dynamic>?) ?? [])
          .map((item) => Topic.fromJson(item as Map<String, dynamic>))
          .toList(),
      concepts: parse('concepts'),
      formulas: parse('formulas'),
      examples: parse('examples'),
      points: parse('points'),
    );
  }

  final Chapter chapter;
  final String subjectName;
  final List<Topic> topics;
  final List<Concept> concepts;
  final List<Concept> formulas;
  final List<Concept> examples;
  final List<Concept> points;
}

class SearchResult {
  SearchResult({
    required this.kind,
    required this.id,
    required this.title,
    required this.subtitle,
    this.subjectId,
    this.chapterId,
  });

  factory SearchResult.fromJson(Map<String, dynamic> json) => SearchResult(
        kind: json['kind'] as String,
        id: json['id'] as int,
        title: json['title'] as String,
        subtitle: json['subtitle'] as String? ?? '',
        subjectId: json['subject_id'] as int?,
        chapterId: json['chapter_id'] as int?,
      );

  final String kind;
  final int id;
  final String title;
  final String subtitle;
  final int? subjectId;
  final int? chapterId;
}
