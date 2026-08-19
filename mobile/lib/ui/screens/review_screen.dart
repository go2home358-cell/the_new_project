import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../data/practice_repository.dart';
import '../../models/attempt.dart';
import '../widgets/async_view.dart';

class ReviewScreen extends StatelessWidget {
  const ReviewScreen({super.key, required this.attemptId});

  final int attemptId;

  @override
  Widget build(BuildContext context) {
    final practice = context.read<PracticeRepository>();
    return Scaffold(
      appBar: AppBar(title: const Text('Review')),
      body: AsyncView<List<ReviewItem>>(
        load: () => practice.review(attemptId),
        emptyMessage: 'Nothing to review.',
        builder: (context, items, reload) => ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: items.length,
          separatorBuilder: (context, index) => const SizedBox(height: 12),
          itemBuilder: (context, index) => _ReviewCard(item: items[index], number: index + 1),
        ),
      ),
    );
  }
}

class _ReviewCard extends StatelessWidget {
  const _ReviewCard({required this.item, required this.number});

  final ReviewItem item;
  final int number;

  @override
  Widget build(BuildContext context) {
    final status = item.isCorrect == null
        ? 'Skipped'
        : item.isCorrect!
            ? 'Correct'
            : 'Incorrect';
    final color = item.isCorrect == null
        ? Colors.grey
        : item.isCorrect!
            ? Colors.green
            : Colors.red;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('Q$number', style: const TextStyle(fontWeight: FontWeight.bold)),
                const Spacer(),
                Chip(label: Text(status), side: BorderSide(color: color)),
              ],
            ),
            const SizedBox(height: 8),
            Text(item.question.text, style: const TextStyle(fontSize: 16, height: 1.35)),
            const SizedBox(height: 12),
            ...item.question.options.map((option) {
              final isCorrect = option.id == item.correctOptionId;
              final isChosen = option.id == item.selectedOptionId;
              return ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  isCorrect
                      ? Icons.check_circle
                      : isChosen
                          ? Icons.cancel
                          : Icons.circle_outlined,
                  color: isCorrect
                      ? Colors.green
                      : isChosen
                          ? Colors.red
                          : null,
                  size: 20,
                ),
                title: Text('${option.label}. ${option.text}'),
              );
            }),
            if (item.explanation.isNotEmpty) ...[
              const Divider(),
              Text(item.explanation, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ],
        ),
      ),
    );
  }
}
