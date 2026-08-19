import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_exception.dart';
import '../../data/practice_repository.dart';

/// Asks how many questions to practise, creates the attempt and opens the player.
class PracticeLauncher {
  static Future<void> start(
    BuildContext context, {
    required String mode,
    int? subjectId,
    int? chapterId,
    int? topicId,
    String? difficulty,
  }) async {
    final count = await showModalBottomSheet<int>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('How many questions?', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ),
            for (final option in const [5, 10, 20, 50])
              ListTile(
                title: Text('$option questions'),
                onTap: () => Navigator.of(context).pop(option),
              ),
          ],
        ),
      ),
    );
    if (count == null || !context.mounted) return;

    final practice = context.read<PracticeRepository>();
    final messenger = ScaffoldMessenger.of(context);
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    try {
      final attempt = await practice.startPractice(
        mode: mode,
        subjectId: subjectId,
        chapterId: chapterId,
        topicId: topicId,
        difficulty: difficulty,
        count: count,
      );
      if (!context.mounted) return;
      Navigator.of(context).pop();
      context.push('/attempts/${attempt.id}', extra: attempt);
    } on ApiException catch (exception) {
      if (!context.mounted) return;
      Navigator.of(context).pop();
      messenger.showSnackBar(SnackBar(content: Text(exception.message)));
    }
  }
}
