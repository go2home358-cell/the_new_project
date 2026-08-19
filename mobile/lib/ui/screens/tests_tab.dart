import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_exception.dart';
import '../../core/formatters.dart';
import '../../data/practice_repository.dart';
import '../../models/attempt.dart';
import '../widgets/async_view.dart';

class TestsTab extends StatelessWidget {
  const TestsTab({super.key});

  Future<void> _start(BuildContext context, MockTest test) async {
    final practice = context.read<PracticeRepository>();
    final messenger = ScaffoldMessenger.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(test.title),
        content: Text(
          '${test.totalQuestions} questions in ${formatDuration(test.durationSeconds)}.\n'
          'The timer starts immediately and answers stay hidden until you submit.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Start test')),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    try {
      final attempt = await practice.startTest(test.id);
      if (context.mounted) context.push('/attempts/${attempt.id}', extra: attempt);
    } on ApiException catch (exception) {
      messenger.showSnackBar(SnackBar(content: Text(exception.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final practice = context.read<PracticeRepository>();
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Tests'),
          bottom: const TabBar(tabs: [Tab(text: 'Available'), Tab(text: 'History')]),
        ),
        body: TabBarView(
          children: [
            AsyncView<List<MockTest>>(
              load: practice.tests,
              emptyMessage: 'No tests available yet.',
              builder: (context, tests, reload) => ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: tests.length,
                separatorBuilder: (context, index) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final test = tests[index];
                  return Card(
                    child: ListTile(
                      leading: Icon(test.kind == 'daily' ? Icons.emoji_events_outlined : Icons.timer_outlined),
                      title: Text(test.title),
                      subtitle: Text(
                        '${test.totalQuestions} questions • ${formatDuration(test.durationSeconds)}'
                        '${test.difficulty == null ? '' : ' • ${test.difficulty}'}',
                      ),
                      trailing: FilledButton(onPressed: () => _start(context, test), child: const Text('Start')),
                    ),
                  );
                },
              ),
            ),
            AsyncView<List<AttemptResult>>(
              load: practice.history,
              emptyMessage: 'You have not finished a test yet.',
              builder: (context, history, reload) => ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: history.length,
                separatorBuilder: (context, index) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final result = history[index];
                  return Card(
                    child: ListTile(
                      title: Text('${result.mode == 'mock' ? 'Mock test' : 'Practice'} • score ${formatPercent(result.score)}'),
                      subtitle: Text(
                        '${result.correct}/${result.total} correct • accuracy ${formatPercent(result.accuracy)} • '
                        '${formatDuration(result.timeUsedSeconds)}',
                      ),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      onTap: () => context.push('/results/${result.attemptId}', extra: result),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
