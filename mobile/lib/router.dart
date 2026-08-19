import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'models/attempt.dart';
import 'state/auth_controller.dart';
import 'ui/screens/ai_tutor_screen.dart';
import 'ui/screens/attempt_screen.dart';
import 'ui/screens/badges_screen.dart';
import 'ui/screens/bookmarks_screen.dart';
import 'ui/screens/chapter_screen.dart';
import 'ui/screens/chapters_screen.dart';
import 'ui/screens/forgot_password_screen.dart';
import 'ui/screens/home_shell.dart';
import 'ui/screens/login_screen.dart';
import 'ui/screens/register_screen.dart';
import 'ui/screens/result_screen.dart';
import 'ui/screens/review_screen.dart';
import 'ui/screens/search_screen.dart';
import 'ui/screens/splash_screen.dart';

GoRouter buildRouter(AuthController auth) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: auth,
    redirect: (context, state) {
      final location = state.matchedLocation;
      if (auth.status == AuthStatus.unknown) {
        return location == '/splash' ? null : '/splash';
      }
      final onAuthScreen = const {'/login', '/register', '/forgot-password'}.contains(location);
      if (auth.status == AuthStatus.unauthenticated) {
        return onAuthScreen ? null : '/login';
      }
      if (onAuthScreen || location == '/splash') return '/';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/register', builder: (context, state) => const RegisterScreen()),
      GoRoute(path: '/forgot-password', builder: (context, state) => const ForgotPasswordScreen()),
      GoRoute(path: '/', builder: (context, state) => const HomeShell()),
      GoRoute(
        path: '/subjects/:subjectId',
        builder: (context, state) => ChaptersScreen(
          subjectId: int.parse(state.pathParameters['subjectId']!),
          subjectName: state.uri.queryParameters['name'] ?? 'Chapters',
        ),
      ),
      GoRoute(
        path: '/chapters/:chapterId',
        builder: (context, state) => ChapterScreen(chapterId: int.parse(state.pathParameters['chapterId']!)),
      ),
      GoRoute(
        path: '/attempts/:attemptId',
        builder: (context, state) => AttemptScreen(
          attemptId: int.parse(state.pathParameters['attemptId']!),
          attempt: state.extra as Attempt?,
        ),
      ),
      GoRoute(
        path: '/results/:attemptId',
        builder: (context, state) => ResultScreen(
          attemptId: int.parse(state.pathParameters['attemptId']!),
          result: state.extra as AttemptResult?,
        ),
      ),
      GoRoute(
        path: '/reviews/:attemptId',
        builder: (context, state) => ReviewScreen(attemptId: int.parse(state.pathParameters['attemptId']!)),
      ),
      GoRoute(path: '/bookmarks', builder: (context, state) => const BookmarksScreen()),
      GoRoute(path: '/badges', builder: (context, state) => const BadgesScreen()),
      GoRoute(path: '/search', builder: (context, state) => const SearchScreen()),
      GoRoute(path: '/ai', builder: (context, state) => const AiTutorScreen()),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(child: Text('Page not found: ${state.uri}')),
    ),
  );
}
