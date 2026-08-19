import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/formatters.dart';
import '../../data/practice_repository.dart';
import '../../data/progress_repository.dart';
import '../../models/progress.dart';
import '../../state/auth_controller.dart';
import '../widgets/async_view.dart';
import '../widgets/section_header.dart';
import '../widgets/stat_tile.dart';
import 'practice_launcher.dart';

class HomeTab extends StatelessWidget {
  const HomeTab({super.key});

  @override
  Widget build(BuildContext context) {
    final progress = context.read<ProgressRepository>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Science Study'),
        actions: [
          IconButton(onPressed: () => context.push('/search'), icon: const Icon(Icons.search)),
          IconButton(onPressed: () => context.push('/bookmarks'), icon: const Icon(Icons.bookmark_outline)),
          IconButton(onPressed: () => context.push('/ai'), icon: const Icon(Icons.smart_toy_outlined)),
          IconButton(
            tooltip: 'Log out',
            onPressed: () => context.read<AuthController>().logout(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: AsyncView<Dashboard>(
        load: progress.dashboard,
        builder: (context, dashboard, reload) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Text(
              'Hi ${dashboard.userName.split(' ').first} 👋',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            Text('Level ${dashboard.summary.level} • ${dashboard.summary.xp} XP'),
            const SizedBox(height: 16),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.7,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              children: [
                StatTile(
                  label: 'Questions solved',
                  value: '${dashboard.summary.questionsAttempted}',
                  icon: Icons.quiz_outlined,
                ),
                StatTile(
                  label: 'Accuracy',
                  value: formatPercent(dashboard.summary.accuracy),
                  icon: Icons.track_changes,
                ),
                StatTile(
                  label: 'Day streak',
                  value: '${dashboard.summary.streakCount}',
                  icon: Icons.local_fire_department_outlined,
                  color: Colors.deepOrange,
                ),
                StatTile(
                  label: 'Tests done',
                  value: '${dashboard.summary.testsCompleted}',
                  icon: Icons.assignment_turned_in_outlined,
                ),
              ],
            ),
            if (dashboard.continueLearning != null) ...[
              const SectionHeader(title: 'Continue learning'),
              Card(
                child: ListTile(
                  title: Text(dashboard.continueLearning!.chapterName),
                  subtitle: Text(
                    '${dashboard.continueLearning!.subjectName} • '
                    '${formatPercent(dashboard.continueLearning!.completionPercent)} complete',
                  ),
                  trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                  onTap: () => context.push('/chapters/${dashboard.continueLearning!.chapterId}'),
                ),
              ),
            ],
            const SectionHeader(title: 'Quick practice'),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => PracticeLauncher.start(context, mode: 'random'),
                    icon: const Icon(Icons.shuffle),
                    label: const Text('Random'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => PracticeLauncher.start(context, mode: 'wrong'),
                    icon: const Icon(Icons.replay),
                    label: const Text('Wrong ones'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => PracticeLauncher.start(context, mode: 'weak'),
                    icon: const Icon(Icons.trending_down),
                    label: const Text('Weak topics'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => PracticeLauncher.start(context, mode: 'bookmark'),
                    icon: const Icon(Icons.bookmark_outline),
                    label: const Text('Bookmarked'),
                  ),
                ),
              ],
            ),
            if (dashboard.dailyChallengeTestId != null) ...[
              const SectionHeader(title: 'Daily challenge'),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.emoji_events_outlined),
                  title: Text('${dashboard.dailyChallengeQuestions} questions, timed'),
                  subtitle: const Text('Keep your streak alive'),
                  trailing: FilledButton(
                    onPressed: () async {
                      final practice = context.read<PracticeRepository>();
                      final attempt = await practice.startTest(dashboard.dailyChallengeTestId!);
                      if (context.mounted) context.push('/attempts/${attempt.id}', extra: attempt);
                    },
                    child: const Text('Start'),
                  ),
                ),
              ),
            ],
            const SectionHeader(title: 'Subject performance'),
            ...dashboard.subjects.map(
              (subject) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(child: Text(subject.name, style: const TextStyle(fontWeight: FontWeight.w600))),
                            Text(formatPercent(subject.accuracy)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        LinearProgressIndicator(value: (subject.completionPercent / 100).clamp(0, 1)),
                        const SizedBox(height: 6),
                        Text('${subject.attempted} attempted • ${subject.correct} correct',
                            style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
