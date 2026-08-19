import '../core/api_client.dart';
import '../models/progress.dart';

class BookmarkRepository {
  BookmarkRepository(this._api);

  final ApiClient _api;

  Future<List<Bookmark>> list({String? targetType}) async {
    final data = await _api.get('/bookmarks', query: {'target_type': targetType}) as List<dynamic>;
    return data.map((item) => Bookmark.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<Bookmark> add({required String targetType, required int targetId, String note = ''}) async {
    final data = await _api.post('/bookmarks', body: {
      'target_type': targetType,
      'target_id': targetId,
      'note': note,
    });
    return Bookmark.fromJson(data as Map<String, dynamic>);
  }

  Future<void> remove({required String targetType, required int targetId}) =>
      _api.delete('/bookmarks', query: {'target_type': targetType, 'target_id': targetId});

  Future<void> removeById(int bookmarkId) => _api.delete('/bookmarks/$bookmarkId');
}
