import 'package:flutter_test/flutter_test.dart';
import 'package:science_study/core/api_client.dart';
import 'package:science_study/core/api_exception.dart';
import 'package:science_study/core/token_storage.dart';
import 'package:science_study/data/auth_repository.dart';
import 'package:science_study/state/auth_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/fake_http_client.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  AuthController controller(FakeHttpClient http) {
    final storage = TokenStorage();
    final api = ApiClient(baseUrl: 'http://localhost/api/v1', storage: storage, httpClient: http);
    return AuthController(AuthRepository(api, storage));
  }

  test('restoreSession stays unauthenticated without a stored token', () async {
    final auth = controller(FakeHttpClient());
    await auth.restoreSession();
    expect(auth.status, AuthStatus.unauthenticated);
  });

  test('login stores tokens and exposes the user', () async {
    final http = FakeHttpClient()
      ..stub(
        'POST',
        '/auth/login',
        200,
        {
          'access_token': 'access-1',
          'refresh_token': 'refresh-1',
          'user': {'id': 1, 'name': 'Sandesh', 'email': 'sandesh@example.com', 'role': 'student'},
        },
      );

    final auth = controller(http);
    final ok = await auth.login(email: 'sandesh@example.com', password: 'secret123');

    expect(ok, isTrue);
    expect(auth.status, AuthStatus.authenticated);
    expect(auth.user!.name, 'Sandesh');
    expect(await TokenStorage().accessToken(), 'access-1');
  });

  test('login surfaces the API error message and stays unauthenticated', () async {
    final http = FakeHttpClient()..stub('POST', '/auth/login', 401, {'detail': 'Invalid email or password'});

    final auth = controller(http);
    final ok = await auth.login(email: 'nobody@example.com', password: 'nope');

    expect(ok, isFalse);
    expect(auth.error, 'Invalid email or password');
    expect(auth.status, AuthStatus.unauthenticated);
  });

  test('logout clears the stored session', () async {
    final http = FakeHttpClient()
      ..stub('POST', '/auth/login', 200, {
        'access_token': 'access-1',
        'refresh_token': 'refresh-1',
        'user': {'id': 1, 'name': 'Sandesh', 'email': 'sandesh@example.com', 'role': 'student'},
      })
      ..stub('POST', '/auth/logout', 200, {'detail': 'ok'});

    final auth = controller(http);
    await auth.login(email: 'sandesh@example.com', password: 'secret123');
    await auth.logout();

    expect(auth.status, AuthStatus.unauthenticated);
    expect(auth.user, isNull);
    expect(await TokenStorage().accessToken(), isNull);
  });

  test('api client refreshes the access token once after a 401', () async {
    SharedPreferences.setMockInitialValues({'access_token': 'stale', 'refresh_token': 'refresh-1'});
    final http = FakeHttpClient()
      ..stubSequence('GET', '/auth/me', [
        (401, {'detail': 'Token expired'}),
        (200, {'id': 1, 'name': 'Sandesh', 'email': 'sandesh@example.com', 'role': 'student'}),
      ])
      ..stub('POST', '/auth/refresh', 200, {'access_token': 'fresh', 'refresh_token': 'refresh-2'});

    final storage = TokenStorage();
    final api = ApiClient(baseUrl: 'http://localhost/api/v1', storage: storage, httpClient: http);
    final auth = AuthController(AuthRepository(api, storage));

    await auth.restoreSession();

    expect(auth.status, AuthStatus.authenticated);
    expect(await storage.accessToken(), 'fresh');
  });

  test('api client gives up and expires the session when refresh fails', () async {
    SharedPreferences.setMockInitialValues({'access_token': 'stale', 'refresh_token': 'dead'});
    final http = FakeHttpClient()
      ..stub('GET', '/auth/me', 401, {'detail': 'Token expired'})
      ..stub('POST', '/auth/refresh', 401, {'detail': 'Invalid refresh token'});

    final storage = TokenStorage();
    final api = ApiClient(baseUrl: 'http://localhost/api/v1', storage: storage, httpClient: http);
    final auth = AuthController(AuthRepository(api, storage));
    api.onSessionExpired = auth.onSessionExpired;

    await auth.restoreSession();

    expect(auth.status, AuthStatus.unauthenticated);
    expect(await storage.accessToken(), isNull);
    expect(() => api.get('/auth/me'), throwsA(isA<ApiException>()));
  });
}
