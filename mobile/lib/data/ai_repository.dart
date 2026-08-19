import '../core/api_client.dart';
import '../models/progress.dart';

class AiRepository {
  AiRepository(this._api);

  final ApiClient _api;

  Future<AiAnswer> ask({
    required String question,
    String language = 'en',
    int? questionId,
    int? chapterId,
  }) async {
    final data = await _api.post('/ai/ask', body: {
      'question': question,
      'language': language,
      'question_id': ?questionId,
      'chapter_id': ?chapterId,
    });
    return AiAnswer.fromJson(data as Map<String, dynamic>);
  }
}
