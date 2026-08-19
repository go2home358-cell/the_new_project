import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../data/bookmark_repository.dart';
import '../../models/progress.dart';
import '../widgets/async_view.dart';
import 'practice_launcher.dart';

class BookmarksScreen extends StatelessWidget {
  const BookmarksScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final bookmarks = context.read<BookmarkRepository>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bookmarks'),
        actions: [
          TextButton(
            onPressed: () => PracticeLauncher.start(context, mode: 'bookmark'),
            child: const Text('Practise'),
          ),
        ],
      ),
      body: AsyncView<List<Bookmark>>(
        load: bookmarks.list,
        emptyMessage: 'Bookmark questions and concepts to find them here.',
        builder: (context, items, reload) => ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: items.length,
          separatorBuilder: (context, index) => const SizedBox(height: 10),
          itemBuilder: (context, index) {
            final bookmark = items[index];
            return Card(
              child: ListTile(
                leading: Icon(bookmark.targetType == 'question' ? Icons.quiz_outlined : Icons.menu_book_outlined),
                title: Text(bookmark.title),
                subtitle: bookmark.subtitle.isEmpty ? null : Text(bookmark.subtitle),
                trailing: IconButton(
                  tooltip: 'Remove',
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () async {
                    await bookmarks.removeById(bookmark.id);
                    await reload();
                  },
                ),
              ),
            );
          },
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.pop(),
        child: const Icon(Icons.arrow_back),
      ),
    );
  }
}
