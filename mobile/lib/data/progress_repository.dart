import '../core/api_client.dart';
import '../models/progress.dart';

class ProgressRepository {
  ProgressRepository(this._api);

  final ApiClient _api;

  Future<Dashboard> dashboard() async {
    final data = await _api.get('/dashboard');
    return Dashboard.fromJson(data as Map<String, dynamic>);
  }

  Future<ProgressSummary> summary() async {
    final data = await _api.get('/progress/summary');
    return ProgressSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<List<ScopePerformance>> subjectPerformance() async {
    final data = await _api.get('/progress/subjects') as List<dynamic>;
    return data.map((item) => ScopePerformance.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<ScopePerformance>> chapterPerformance(int subjectId) async {
    final data = await _api.get('/progress/chapters', query: {'subject_id': subjectId}) as List<dynamic>;
    return data.map((item) => ScopePerformance.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<WeakTopic>> weakTopics() async {
    final data = await _api.get('/progress/weak-topics') as List<dynamic>;
    return data.map((item) => WeakTopic.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<List<AchievementBadge>> badges() async {
    final data = await _api.get('/badges') as List<dynamic>;
    return data.map((item) => AchievementBadge.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<void> logStudyTime(int seconds, {int? subjectId, int? chapterId}) => _api.post('/study-sessions', body: {
        'seconds': seconds,
        'subject_id': ?subjectId,
        'chapter_id': ?chapterId,
      });
}
