import 'package:flutter/material.dart';

import 'app.dart';
import 'core/api_client.dart';
import 'core/config.dart';
import 'core/token_storage.dart';
import 'data/ai_repository.dart';
import 'data/auth_repository.dart';
import 'data/bookmark_repository.dart';
import 'data/content_repository.dart';
import 'data/practice_repository.dart';
import 'data/progress_repository.dart';

void main() {
  final storage = TokenStorage();
  final api = ApiClient(baseUrl: AppConfig.apiBaseUrl, storage: storage);
  runApp(
    ScienceStudyApp(
      api: api,
      auth: AuthRepository(api, storage),
      content: ContentRepository(api),
      practice: PracticeRepository(api),
      progress: ProgressRepository(api),
      bookmarks: BookmarkRepository(api),
      ai: AiRepository(api),
    ),
  );
}
