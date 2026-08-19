import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/progress_repository.dart';
import '../../models/progress.dart';
import '../widgets/async_view.dart';

class BadgesScreen extends StatelessWidget {
  const BadgesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final progress = context.read<ProgressRepository>();
    return Scaffold(
      appBar: AppBar(title: const Text('Badges')),
      body: AsyncView<List<AchievementBadge>>(
        load: progress.badges,
        emptyMessage: 'No badges configured.',
        builder: (context, badges, reload) => ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: badges.length,
          separatorBuilder: (context, index) => const SizedBox(height: 10),
          itemBuilder: (context, index) {
            final badge = badges[index];
            return Card(
              child: ListTile(
                leading: Text(badge.icon, style: const TextStyle(fontSize: 24)),
                title: Text(badge.title),
                subtitle: Text(badge.description),
                trailing: Icon(
                  badge.earned ? Icons.verified : Icons.lock_outline,
                  color: badge.earned ? Colors.amber.shade700 : null,
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
