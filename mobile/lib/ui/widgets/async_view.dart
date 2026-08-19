import 'package:flutter/material.dart';

import '../../core/api_exception.dart';

/// Loads a future and renders loading / error / empty / data states with a
/// pull-to-refresh retry, so every screen behaves consistently.
class AsyncView<T> extends StatefulWidget {
  const AsyncView({super.key, required this.load, required this.builder, this.emptyMessage});

  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data, Future<void> Function() reload) builder;
  final String? emptyMessage;

  @override
  State<AsyncView<T>> createState() => _AsyncViewState<T>();
}

class _AsyncViewState<T> extends State<AsyncView<T>> {
  late Future<T> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.load();
  }

  Future<void> _reload() async {
    setState(() => _future = widget.load());
    await _future.catchError((Object error) => Future<T>.error(error));
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          final error = snapshot.error;
          return ErrorRetry(
            message: error is ApiException ? error.message : 'Something went wrong.',
            onRetry: _reload,
          );
        }
        final data = snapshot.data as T;
        if (data is List && data.isEmpty && widget.emptyMessage != null) {
          return RefreshIndicator(
            onRefresh: _reload,
            child: ListView(
              children: [
                const SizedBox(height: 120),
                Center(child: Text(widget.emptyMessage!, textAlign: TextAlign.center)),
              ],
            ),
          );
        }
        return RefreshIndicator(onRefresh: _reload, child: widget.builder(context, data, _reload));
      },
    );
  }
}

class ErrorRetry extends StatelessWidget {
  const ErrorRetry({super.key, required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.cloud_off, size: 48, color: Theme.of(context).colorScheme.error),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            OutlinedButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
