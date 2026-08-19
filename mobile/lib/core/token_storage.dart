import 'package:shared_preferences/shared_preferences.dart';

/// Persists the JWT pair and the cached profile name between app launches.
class TokenStorage {
  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';

  Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  Future<String?> accessToken() async => (await _prefs).getString(_accessKey);

  Future<String?> refreshToken() async => (await _prefs).getString(_refreshKey);

  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    final prefs = await _prefs;
    await prefs.setString(_accessKey, accessToken);
    await prefs.setString(_refreshKey, refreshToken);
  }

  Future<void> clear() async {
    final prefs = await _prefs;
    await prefs.remove(_accessKey);
    await prefs.remove(_refreshKey);
  }
}
