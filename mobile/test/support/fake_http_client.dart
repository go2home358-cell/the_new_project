import 'dart:convert';

import 'package:http/http.dart' as http;

/// Minimal stub client: queues canned JSON responses per method and path so the
/// repositories and controllers can be tested without a running backend.
class FakeHttpClient extends http.BaseClient {
  final Map<String, List<(int, Object)>> _responses = {};
  final List<String> requests = [];

  void stub(String method, String path, int statusCode, Object body) {
    _responses.putIfAbsent('$method $path', () => []).add((statusCode, body));
  }

  void stubSequence(String method, String path, List<(int, Object)> responses) {
    _responses.putIfAbsent('$method $path', () => []).addAll(responses);
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final key = '${request.method} ${request.url.path.replaceFirst('/api/v1', '')}';
    requests.add(key);
    final queue = _responses[key];
    if (queue == null || queue.isEmpty) {
      return _response(404, {'detail': 'No stub for $key'});
    }
    final (statusCode, body) = queue.length == 1 ? queue.first : queue.removeAt(0);
    return _response(statusCode, body);
  }

  http.StreamedResponse _response(int statusCode, Object body) {
    final bytes = utf8.encode(jsonEncode(body));
    return http.StreamedResponse(
      Stream.value(bytes),
      statusCode,
      headers: {'content-type': 'application/json'},
      contentLength: bytes.length,
    );
  }
}
