import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/formatters.dart';
import '../../data/content_repository.dart';
import '../../models/content.dart';
import '../widgets/async_view.dart';
import 'practice_launcher.dart';

class ChaptersScreen extends StatelessWidget {
  const ChaptersScreen({super.key, required this.subjectId, required this.subjectName});

  final int subjectId;
  final String subjectName;

  @override
  Widget build(BuildContext context) {
    final content = context.read<ContentRepository>();
    return Scaffold(
      appBar: AppBar(title: Text(subjectName)),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => PracticeLauncher.start(context, mode: 'random', subjectId: subjectId),
        icon: const Icon(Icons.play_arrow),
        label: const Text('Practise subject'),
      ),
      body: AsyncView<List<Chapter>>(
        load: () => content.chapters(subjectId),
        emptyMessage: 'This subject has no chapters yet.',
        builder: (context, chapters, reload) => ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          itemCount: chapters.length,
          separatorBuilder: (context, index) => const SizedBox(height: 10),
          itemBuilder: (context, index) {
            final chapter = chapters[index];
            return Card(
              child: ListTile(
                title: Text(chapter.name),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 6),
                    Text('${chapter.questionCount} questions • ${formatPercent(chapter.completionPercent)} complete'),
                    const SizedBox(height: 6),
                    LinearProgressIndicator(value: (chapter.completionPercent / 100).clamp(0, 1)),
                  ],
                ),
                trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                onTap: () => context.push('/chapters/${chapter.id}'),
              ),
            );
          },
        ),
      ),
    );
  }
}
