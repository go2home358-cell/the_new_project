import '../core/api_client.dart';
import '../core/token_storage.dart';
import '../models/user.dart';

class AuthRepository {
  AuthRepository(this._api, this._storage);

  final ApiClient _api;
  final TokenStorage _storage;

  Future<AppUser> register({required String name, required String email, required String password}) async {
    final data = await _api.post('/auth/register', body: {'name': name, 'email': email, 'password': password});
    return _persist(data as Map<String, dynamic>);
  }

  Future<AppUser> login({required String email, required String password}) async {
    final data = await _api.post('/auth/login', body: {'email': email, 'password': password});
    return _persist(data as Map<String, dynamic>);
  }

  Future<AppUser> me() async {
    final data = await _api.get('/auth/me');
    return AppUser.fromJson(data as Map<String, dynamic>);
  }

  /// Returns the reset token when the backend runs in development mode.
  Future<String?> forgotPassword(String email) async {
    final data = await _api.post('/auth/forgot-password', body: {'email': email});
    return (data as Map<String, dynamic>)['reset_token'] as String?;
  }

  Future<void> resetPassword({required String token, required String newPassword}) =>
      _api.post('/auth/reset-password', body: {'reset_token': token, 'new_password': newPassword});

  Future<void> logout() async {
    try {
      await _api.post('/auth/logout');
    } finally {
      await _storage.clear();
    }
  }

  Future<bool> hasSession() async => (await _storage.accessToken()) != null;

  Future<AppUser> _persist(Map<String, dynamic> data) async {
    await _storage.saveTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
    );
    return AppUser.fromJson(data['user'] as Map<String, dynamic>);
  }
}
