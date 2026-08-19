import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_exception.dart';
import '../../data/bookmark_repository.dart';
import '../../data/content_repository.dart';
import '../../models/content.dart';
import '../widgets/async_view.dart';
import 'practice_launcher.dart';

class ChapterScreen extends StatelessWidget {
  const ChapterScreen({super.key, required this.chapterId});

  final int chapterId;

  @override
  Widget build(BuildContext context) {
    final content = context.read<ContentRepository>();
    return AsyncView<ChapterDetail>(
      load: () => content.chapter(chapterId),
      builder: (context, detail, reload) => DefaultTabController(
        length: 4,
        child: Scaffold(
          appBar: AppBar(
            title: Text(detail.chapter.name),
            bottom: const TabBar(
              isScrollable: true,
              tabAlignment: TabAlignment.start,
              tabs: [
                Tab(text: 'Concepts'),
                Tab(text: 'Formulas'),
                Tab(text: 'Examples'),
                Tab(text: 'Revision'),
              ],
            ),
          ),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: () => PracticeLauncher.start(context, mode: 'topic', chapterId: chapterId),
            icon: const Icon(Icons.quiz_outlined),
            label: const Text('Practise chapter'),
          ),
          body: TabBarView(
            children: [
              _ConceptList(items: detail.concepts, topics: detail.topics, chapterId: chapterId, onChanged: reload),
              _ConceptList(items: detail.formulas, onChanged: reload),
              _ConceptList(items: detail.examples, onChanged: reload),
              _ConceptList(items: detail.points, onChanged: reload),
            ],
          ),
        ),
      ),
    );
  }
}

class _ConceptList extends StatelessWidget {
  const _ConceptList({required this.items, required this.onChanged, this.topics, this.chapterId});

  final List<Concept> items;
  final Future<void> Function() onChanged;
  final List<Topic>? topics;
  final int? chapterId;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty && (topics == null || topics!.isEmpty)) {
      return const Center(child: Text('Nothing here yet.'));
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
      children: [
        if (topics != null && topics!.isNotEmpty) ...[
          Text('Topics', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: topics!
                .map(
                  (topic) => ActionChip(
                    label: Text('${topic.name} (${topic.questionCount})'),
                    onPressed: () => PracticeLauncher.start(
                      context,
                      mode: 'topic',
                      chapterId: chapterId,
                      topicId: topic.id,
                    ),
                  ),
                )
                .toList(),
          ),
          const Divider(height: 32),
        ],
        ...items.map((concept) => _ConceptCard(concept: concept, onChanged: onChanged)),
      ],
    );
  }
}

class _ConceptCard extends StatelessWidget {
  const _ConceptCard({required this.concept, required this.onChanged});

  final Concept concept;
  final Future<void> Function() onChanged;

  Future<void> _toggleBookmark(BuildContext context) async {
    final bookmarks = context.read<BookmarkRepository>();
    final messenger = ScaffoldMessenger.of(context);
    try {
      if (concept.isBookmarked) {
        await bookmarks.remove(targetType: 'concept', targetId: concept.id);
      } else {
        await bookmarks.add(targetType: 'concept', targetId: concept.id);
      }
      await onChanged();
    } on ApiException catch (exception) {
      messenger.showSnackBar(SnackBar(content: Text(exception.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(concept.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ),
                  IconButton(
                    tooltip: concept.isBookmarked ? 'Remove bookmark' : 'Bookmark',
                    onPressed: () => _toggleBookmark(context),
                    icon: Icon(concept.isBookmarked ? Icons.bookmark : Icons.bookmark_outline),
                  ),
                ],
              ),
              if (concept.body.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(concept.body, style: const TextStyle(height: 1.4)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
