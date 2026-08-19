import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_exception.dart';
import '../../data/ai_repository.dart';
import '../../models/progress.dart';

class AiTutorScreen extends StatefulWidget {
  const AiTutorScreen({super.key});

  @override
  State<AiTutorScreen> createState() => _AiTutorScreenState();
}

class _AiTutorScreenState extends State<AiTutorScreen> {
  final _question = TextEditingController();
  String _language = 'en';
  AiAnswer? _answer;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _question.dispose();
    super.dispose();
  }

  Future<void> _ask() async {
    if (_question.text.trim().length < 3) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final answer = await context.read<AiRepository>().ask(question: _question.text.trim(), language: _language);
      if (mounted) setState(() => _answer = answer);
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI tutor')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'en', label: Text('English')),
              ButtonSegment(value: 'mr', label: Text('मराठी')),
            ],
            selected: {_language},
            onSelectionChanged: (values) => setState(() => _language = values.first),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _question,
            minLines: 2,
            maxLines: 5,
            decoration: const InputDecoration(
              labelText: 'Ask about any concept',
              hintText: 'e.g. Explain Newton\'s second law with an example',
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _loading ? null : _ask,
            icon: const Icon(Icons.send),
            label: Text(_loading ? 'Thinking…' : 'Ask'),
          ),
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          if (_answer != null) ...[
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(_answer!.isUnavailable ? Icons.info_outline : Icons.smart_toy_outlined),
                        const SizedBox(width: 8),
                        Text(
                          _answer!.isUnavailable ? 'AI not configured' : 'Source: ${_answer!.source}',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(_answer!.answer, style: const TextStyle(height: 1.4)),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
