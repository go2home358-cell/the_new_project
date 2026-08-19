import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/formatters.dart';
import '../../data/content_repository.dart';
import '../../models/content.dart';
import '../widgets/async_view.dart';

class SubjectsTab extends StatelessWidget {
  const SubjectsTab({super.key});

  @override
  Widget build(BuildContext context) {
    final content = context.read<ContentRepository>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Subjects'),
        actions: [IconButton(onPressed: () => context.push('/search'), icon: const Icon(Icons.search))],
      ),
      body: AsyncView<List<Subject>>(
        load: content.subjects,
        emptyMessage: 'No subjects yet. Seed the backend database to get started.',
        builder: (context, subjects, reload) => ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: subjects.length,
          separatorBuilder: (context, index) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final subject = subjects[index];
            return Card(
              child: InkWell(
                borderRadius: BorderRadius.circular(16),
                onTap: () => context.push('/subjects/${subject.id}?name=${Uri.encodeComponent(subject.name)}'),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              subject.name,
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                            ),
                          ),
                          Text(formatPercent(subject.completionPercent)),
                        ],
                      ),
                      if (subject.description.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(subject.description, style: Theme.of(context).textTheme.bodySmall),
                      ],
                      const SizedBox(height: 10),
                      LinearProgressIndicator(value: (subject.completionPercent / 100).clamp(0, 1)),
                      const SizedBox(height: 10),
                      Text('${subject.chapterCount} chapters • ${subject.questionCount} questions',
                          style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
