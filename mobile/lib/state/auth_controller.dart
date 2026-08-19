import 'package:flutter/foundation.dart';

import '../core/api_exception.dart';
import '../data/auth_repository.dart';
import '../models/user.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthController extends ChangeNotifier {
  AuthController(this._repository);

  final AuthRepository _repository;

  AuthStatus status = AuthStatus.unknown;
  AppUser? user;
  bool busy = false;
  String? error;

  Future<void> restoreSession() async {
    if (!await _repository.hasSession()) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    try {
      user = await _repository.me();
      status = AuthStatus.authenticated;
    } on ApiException {
      status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<bool> login({required String email, required String password}) =>
      _run(() => _repository.login(email: email, password: password));

  Future<bool> register({required String name, required String email, required String password}) =>
      _run(() => _repository.register(name: name, email: email, password: password));

  Future<String?> forgotPassword(String email) async {
    _setBusy(true);
    try {
      return await _repository.forgotPassword(email);
    } on ApiException catch (exception) {
      error = exception.message;
      return null;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> resetPassword({required String token, required String newPassword}) async {
    _setBusy(true);
    try {
      await _repository.resetPassword(token: token, newPassword: newPassword);
      return true;
    } on ApiException catch (exception) {
      error = exception.message;
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<void> refreshProfile() async {
    try {
      user = await _repository.me();
      notifyListeners();
    } on ApiException {
      // keep the cached profile; the next request will surface the problem
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    user = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  /// Called by the API client when the refresh token is no longer valid.
  void onSessionExpired() {
    user = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  Future<bool> _run(Future<AppUser> Function() action) async {
    _setBusy(true);
    try {
      user = await action();
      status = AuthStatus.authenticated;
      return true;
    } on ApiException catch (exception) {
      error = exception.message;
      status = AuthStatus.unauthenticated;
      return false;
    } finally {
      _setBusy(false);
    }
  }

  void _setBusy(bool value) {
    busy = value;
    if (value) error = null;
    notifyListeners();
  }
}
