import '../core/api_client.dart';
import '../models/attempt.dart';

class PracticeRepository {
  PracticeRepository(this._api);

  final ApiClient _api;

  Future<Attempt> startPractice({
    required String mode,
    int? subjectId,
    int? chapterId,
    int? topicId,
    String? difficulty,
    int count = 10,
  }) async {
    final data = await _api.post('/practice/sessions', body: {
      'mode': mode,
      'subject_id': ?subjectId,
      'chapter_id': ?chapterId,
      'topic_id': ?topicId,
      'difficulty': ?difficulty,
      'count': count,
    });
    return Attempt.fromJson(data as Map<String, dynamic>);
  }

  Future<List<MockTest>> tests({int? subjectId, String? kind}) async {
    final data = await _api.get('/tests', query: {'subject_id': subjectId, 'kind': kind}) as List<dynamic>;
    return data.map((item) => MockTest.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<Attempt> startTest(int testId) async {
    final data = await _api.post('/tests/$testId/start');
    return Attempt.fromJson(data as Map<String, dynamic>);
  }

  Future<Attempt> attempt(int attemptId) async {
    final data = await _api.get('/attempts/$attemptId');
    return Attempt.fromJson(data as Map<String, dynamic>);
  }

  Future<AnswerFeedback> answer({
    required int attemptId,
    required int questionId,
    int? selectedOptionId,
    bool markedForReview = false,
    int timeSpentSeconds = 0,
  }) async {
    final data = await _api.post('/attempts/$attemptId/answers', body: {
      'question_id': questionId,
      'selected_option_id': selectedOptionId,
      'marked_for_review': markedForReview,
      'time_spent_seconds': timeSpentSeconds,
    });
    return AnswerFeedback.fromJson(data as Map<String, dynamic>);
  }

  Future<AttemptResult> submit(int attemptId) async {
    final data = await _api.post('/attempts/$attemptId/submit');
    return AttemptResult.fromJson(data as Map<String, dynamic>);
  }

  Future<AttemptResult> result(int attemptId) async {
    final data = await _api.get('/attempts/$attemptId/result');
    return AttemptResult.fromJson(data as Map<String, dynamic>);
  }

  Future<List<ReviewItem>> review(int attemptId) async {
    final data = await _api.get('/attempts/$attemptId/review') as List<dynamic>;
    return data.map((item) => ReviewItem.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<AttemptResult>> history({int limit = 20}) async {
    final data = await _api.get('/attempts', query: {'limit': limit}) as List<dynamic>;
    return data.map((item) => AttemptResult.fromJson(item as Map<String, dynamic>)).toList();
  }
}
