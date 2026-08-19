import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_exception.dart';
import '../../data/content_repository.dart';
import '../../models/content.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _controller = TextEditingController();
  List<SearchResult> _results = [];
  bool _loading = false;
  String? _error;
  bool _searched = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search(String query) async {
    if (query.trim().length < 2) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await context.read<ContentRepository>().search(query.trim());
      if (!mounted) return;
      setState(() {
        _results = results;
        _searched = true;
      });
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: true,
          textInputAction: TextInputAction.search,
          onSubmitted: _search,
          decoration: const InputDecoration(hintText: 'Search chapters, topics, questions'),
        ),
        actions: [IconButton(onPressed: () => _search(_controller.text), icon: const Icon(Icons.search))],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : !_searched
                  ? const Center(child: Text('Type at least two characters and hit search.'))
                  : _results.isEmpty
                      ? const Center(child: Text('No matches found.'))
                      : ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: _results.length,
                          separatorBuilder: (context, index) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final result = _results[index];
                            return ListTile(
                              leading: Icon(_iconFor(result.kind)),
                              title: Text(result.title),
                              subtitle: Text(result.subtitle.isEmpty ? result.kind : result.subtitle),
                              onTap: result.chapterId == null
                                  ? null
                                  : () => context.push('/chapters/${result.chapterId}'),
                            );
                          },
                        ),
    );
  }

  IconData _iconFor(String kind) {
    switch (kind) {
      case 'subject':
        return Icons.science_outlined;
      case 'chapter':
        return Icons.menu_book_outlined;
      case 'topic':
        return Icons.label_outline;
      default:
        return Icons.quiz_outlined;
    }
  }
}
