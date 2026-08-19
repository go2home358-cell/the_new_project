import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/formatters.dart';
import '../../data/practice_repository.dart';
import '../../models/attempt.dart';
import '../widgets/async_view.dart';
import '../widgets/section_header.dart';
import '../widgets/stat_tile.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.attemptId, this.result});

  final int attemptId;
  final AttemptResult? result;

  @override
  Widget build(BuildContext context) {
    if (result != null) return _ResultBody(result: result!);
    final practice = context.read<PracticeRepository>();
    return Scaffold(
      appBar: AppBar(title: const Text('Result')),
      body: AsyncView<AttemptResult>(
        load: () => practice.result(attemptId),
        builder: (context, data, reload) => _ResultBody(result: data, embedded: true),
      ),
    );
  }
}

class _ResultBody extends StatelessWidget {
  const _ResultBody({required this.result, this.embedded = false});

  final AttemptResult result;
  final bool embedded;

  @override
  Widget build(BuildContext context) {
    final body = ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        Center(
          child: Column(
            children: [
              Text(
                formatPercent(result.score),
                style: Theme.of(context).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.bold),
              ),
              const Text('score'),
              if (result.xpEarned > 0) Text('+${result.xpEarned} XP'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 1.8,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          children: [
            StatTile(label: 'Correct', value: '${result.correct}', icon: Icons.check_circle_outline, color: Colors.green),
            StatTile(label: 'Incorrect', value: '${result.incorrect}', icon: Icons.cancel_outlined, color: Colors.red),
            StatTile(label: 'Skipped', value: '${result.unattempted}', icon: Icons.remove_circle_outline),
            StatTile(label: 'Accuracy', value: formatPercent(result.accuracy), icon: Icons.track_changes),
            StatTile(label: 'Attempted', value: '${result.attempted}/${result.total}', icon: Icons.list_alt),
            StatTile(label: 'Time used', value: formatDuration(result.timeUsedSeconds), icon: Icons.schedule),
          ],
        ),
        if (result.newBadges.isNotEmpty) ...[
          const SectionHeader(title: 'New badges'),
          Wrap(
            spacing: 8,
            children: result.newBadges.map((badge) => Chip(label: Text(badge))).toList(),
          ),
        ],
        if (result.topicPerformance.isNotEmpty) ...[
          const SectionHeader(title: 'Topic performance'),
          ...result.topicPerformance.map(
            (topic) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(child: Text(topic.topicName)),
                          Text('${topic.correct}/${topic.total}'),
                        ],
                      ),
                      const SizedBox(height: 8),
                      LinearProgressIndicator(value: (topic.accuracy / 100).clamp(0, 1)),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
        if (result.weakTopics.isNotEmpty) ...[
          const SectionHeader(title: 'Focus next on'),
          Wrap(spacing: 8, runSpacing: 8, children: result.weakTopics.map((topic) => Chip(label: Text(topic))).toList()),
        ],
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: () => context.push('/reviews/${result.attemptId}'),
          icon: const Icon(Icons.fact_check_outlined),
          label: const Text('Review answers'),
        ),
        const SizedBox(height: 8),
        OutlinedButton(onPressed: () => context.go('/'), child: const Text('Back to home')),
      ],
    );
    if (embedded) return body;
    return Scaffold(appBar: AppBar(title: const Text('Result')), body: body);
  }
}
