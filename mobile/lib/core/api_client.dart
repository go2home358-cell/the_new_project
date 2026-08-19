import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_exception.dart';
import 'token_storage.dart';

/// Thin JSON client for the Science Study backend.
///
/// It attaches the stored access token, refreshes it once when the API answers
/// 401, and turns error payloads into [ApiException]s the UI can display.
class ApiClient {
  ApiClient({required this.baseUrl, required TokenStorage storage, http.Client? httpClient})
      : _storage = storage,
        _http = httpClient ?? http.Client();

  final String baseUrl;
  final TokenStorage _storage;
  final http.Client _http;

  /// Called when refreshing fails and the user has to log in again.
  void Function()? onSessionExpired;

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final cleaned = query?.entries
        .where((entry) => entry.value != null)
        .map((entry) => MapEntry(entry.key, '${entry.value}'))
        .toList();
    return Uri.parse('$baseUrl$path').replace(
      queryParameters: cleaned == null || cleaned.isEmpty ? null : Map.fromEntries(cleaned),
    );
  }

  Future<Map<String, String>> _headers({bool json = true}) async {
    final token = await _storage.accessToken();
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Credential endpoints answer 401 for bad input, so a refresh must not be
  /// attempted there: the message from the API is what the user needs to see.
  static const _credentialPaths = {
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/auth/forgot-password',
    '/auth/reset-password',
  };

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) => _send(
        () async => _http.get(_uri(path, query), headers: await _headers(json: false)),
        allowRefresh: !_credentialPaths.contains(path),
      );

  Future<dynamic> post(String path, {Object? body, Map<String, dynamic>? query}) => _send(
        () async => _http.post(
          _uri(path, query),
          headers: await _headers(),
          body: body == null ? null : jsonEncode(body),
        ),
        allowRefresh: !_credentialPaths.contains(path),
      );

  Future<dynamic> delete(String path, {Map<String, dynamic>? query}) => _send(
        () async => _http.delete(_uri(path, query), headers: await _headers(json: false)),
        allowRefresh: !_credentialPaths.contains(path),
      );

  Future<dynamic> _send(Future<http.Response> Function() request, {bool allowRefresh = true}) async {
    http.Response response;
    try {
      response = await request().timeout(const Duration(seconds: 30));
    } on TimeoutException {
      throw ApiException('The server took too long to respond.');
    } catch (error) {
      throw ApiException('Cannot reach the server. Check your connection and API URL.');
    }

    if (response.statusCode == 401 && allowRefresh) {
      if (await _refresh()) {
        return _send(request, allowRefresh: false);
      }
      onSessionExpired?.call();
      throw ApiException('Your session expired. Please log in again.', statusCode: 401);
    }

    if (response.statusCode >= 400) {
      throw ApiException(_errorMessage(response), statusCode: response.statusCode);
    }
    if (response.statusCode == 204 || response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  String _errorMessage(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      final detail = decoded is Map<String, dynamic> ? decoded['detail'] : null;
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map && first['msg'] != null) return '${first['msg']}';
      }
    } catch (_) {
      // fall through to the generic message
    }
    return 'Request failed (${response.statusCode}).';
  }

  Future<bool> _refresh() async {
    final refreshToken = await _storage.refreshToken();
    if (refreshToken == null) return false;
    final response = await _http.post(
      _uri('/auth/refresh'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh_token': refreshToken}),
    );
    if (response.statusCode >= 400) {
      await _storage.clear();
      return false;
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    await _storage.saveTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
    );
    return true;
  }
}
