import '../core/api_client.dart';
import '../models/content.dart';
import '../models/question.dart';

class ContentRepository {
  ContentRepository(this._api);

  final ApiClient _api;

  Future<List<Subject>> subjects() async {
    final data = await _api.get('/subjects') as List<dynamic>;
    return data.map((item) => Subject.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<Chapter>> chapters(int subjectId) async {
    final data = await _api.get('/subjects/$subjectId/chapters') as List<dynamic>;
    return data.map((item) => Chapter.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<ChapterDetail> chapter(int chapterId) async {
    final data = await _api.get('/chapters/$chapterId');
    return ChapterDetail.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Question>> questions({int? subjectId, int? chapterId, int? topicId, int limit = 20}) async {
    final data = await _api.get('/questions', query: {
      'subject_id': subjectId,
      'chapter_id': chapterId,
      'topic_id': topicId,
      'limit': limit,
    }) as List<dynamic>;
    return data.map((item) => Question.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<SearchResult>> search(String query) async {
    final data = await _api.get('/search', query: {'q': query}) as Map<String, dynamic>;
    return ((data['results'] as List<dynamic>?) ?? [])
        .map((item) => SearchResult.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
