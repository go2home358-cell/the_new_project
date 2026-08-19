import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/theme.dart';
import 'data/ai_repository.dart';
import 'data/auth_repository.dart';
import 'data/bookmark_repository.dart';
import 'data/content_repository.dart';
import 'data/practice_repository.dart';
import 'data/progress_repository.dart';
import 'router.dart';
import 'state/auth_controller.dart';

class ScienceStudyApp extends StatefulWidget {
  const ScienceStudyApp({
    super.key,
    required this.api,
    required this.auth,
    required this.content,
    required this.practice,
    required this.progress,
    required this.bookmarks,
    required this.ai,
  });

  final ApiClient api;
  final AuthRepository auth;
  final ContentRepository content;
  final PracticeRepository practice;
  final ProgressRepository progress;
  final BookmarkRepository bookmarks;
  final AiRepository ai;

  @override
  State<ScienceStudyApp> createState() => _ScienceStudyAppState();
}

class _ScienceStudyAppState extends State<ScienceStudyApp> {
  late final AuthController _authController;

  @override
  void initState() {
    super.initState();
    _authController = AuthController(widget.auth);
    widget.api.onSessionExpired = _authController.onSessionExpired;
    _authController.restoreSession();
  }

  @override
  void dispose() {
    _authController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider.value(value: widget.content),
        Provider.value(value: widget.practice),
        Provider.value(value: widget.progress),
        Provider.value(value: widget.bookmarks),
        Provider.value(value: widget.ai),
        ChangeNotifierProvider.value(value: _authController),
      ],
      child: MaterialApp.router(
        title: 'Science Study',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        routerConfig: buildRouter(_authController),
      ),
    );
  }
}
