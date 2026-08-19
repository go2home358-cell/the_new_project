import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/formatters.dart';
import '../../core/theme.dart';
import '../../data/bookmark_repository.dart';
import '../../data/practice_repository.dart';
import '../../models/attempt.dart';
import '../../state/attempt_controller.dart';
import '../widgets/async_view.dart';

/// The question player. Practice mode gives instant feedback; timed tests show
/// a countdown, a question palette and reveal answers only after submission.
class AttemptScreen extends StatelessWidget {
  const AttemptScreen({super.key, required this.attemptId, this.attempt});

  final int attemptId;
  final Attempt? attempt;

  @override
  Widget build(BuildContext context) {
    final practice = context.read<PracticeRepository>();
    if (attempt != null) return _AttemptPlayer(attempt: attempt!);
    return Scaffold(
      appBar: AppBar(title: const Text('Loading attempt')),
      body: AsyncView<Attempt>(
        load: () => practice.attempt(attemptId),
        builder: (context, data, reload) => _AttemptPlayer(attempt: data),
      ),
    );
  }
}

class _AttemptPlayer extends StatelessWidget {
  const _AttemptPlayer({required this.attempt});

  final Attempt attempt;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (context) => AttemptController(context.read<PracticeRepository>(), attempt),
      child: const _AttemptBody(),
    );
  }
}

class _AttemptBody extends StatelessWidget {
  const _AttemptBody();

  Future<void> _submit(BuildContext context) async {
    final controller = context.read<AttemptController>();
    final unanswered = controller.attempt.total - controller.answeredCount;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Submit now?'),
        content: Text(
          unanswered == 0
              ? 'All questions answered. Submit for scoring?'
              : '$unanswered question(s) are still unanswered and will be marked as skipped.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Keep going')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Submit')),
        ],
      ),
    );
    if (confirmed != true) return;
    final result = await controller.submit();
    if (result != null && context.mounted) {
      context.pushReplacement('/results/${result.attemptId}', extra: result);
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AttemptController>();
    final question = controller.attempt.questions[controller.index];
    final feedback = controller.currentFeedback;
    final selected = controller.selectedOptions[question.id];
    final revealed = feedback?.revealsAnswer ?? false;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final leave = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Leave this attempt?'),
            content: const Text('Your answers are saved. You can submit it later from the attempt link.'),
            actions: [
              TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Stay')),
              FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Leave')),
            ],
          ),
        );
        if (leave == true && context.mounted) context.pop();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text('Question ${controller.index + 1} of ${controller.attempt.total}'),
          actions: [
            if (controller.attempt.isTimed)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Center(
                  child: Chip(
                    avatar: const Icon(Icons.timer_outlined, size: 18),
                    label: Text(formatDuration(controller.remainingSeconds)),
                    backgroundColor: controller.remainingSeconds < 60
                        ? Theme.of(context).colorScheme.errorContainer
                        : null,
                  ),
                ),
              ),
            IconButton(
              tooltip: 'Question palette',
              onPressed: () => _showPalette(context, controller),
              icon: const Icon(Icons.grid_view),
            ),
          ],
        ),
        bottomNavigationBar: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                OutlinedButton(
                  onPressed: controller.index == 0 ? null : controller.previous,
                  child: const Text('Previous'),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: controller.index == controller.attempt.total - 1
                      ? FilledButton(
                          onPressed: controller.submitting ? null : () => _submit(context),
                          child: Text(controller.submitting ? 'Submitting…' : 'Submit'),
                        )
                      : FilledButton(onPressed: controller.next, child: const Text('Next')),
                ),
              ],
            ),
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            if (controller.expired)
              Card(
                color: Theme.of(context).colorScheme.errorContainer,
                child: const Padding(
                  padding: EdgeInsets.all(12),
                  child: Text('Time is up. Submit to see your result.'),
                ),
              ),
            Row(
              children: [
                Chip(
                  label: Text(question.difficulty),
                  side: BorderSide(color: AppTheme.difficultyColor(context, question.difficulty)),
                ),
                const Spacer(),
                IconButton(
                  tooltip: 'Bookmark question',
                  onPressed: () => _bookmark(context, question.id),
                  icon: const Icon(Icons.bookmark_add_outlined),
                ),
                IconButton(
                  tooltip: 'Mark for review',
                  onPressed: controller.toggleMarkForReview,
                  icon: Icon(
                    (controller.markedForReview[question.id] ?? false) ? Icons.flag : Icons.flag_outlined,
                    color: (controller.markedForReview[question.id] ?? false) ? Colors.purple : null,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(question.text, style: const TextStyle(fontSize: 17, height: 1.4)),
            if (question.imageUrl != null) ...[
              const SizedBox(height: 12),
              Image.network(question.imageUrl!, errorBuilder: (context, error, stack) => const SizedBox.shrink()),
            ],
            const SizedBox(height: 16),
            ...question.options.map((option) {
              final isSelected = selected == option.id;
              final isCorrect = revealed && feedback!.correctOptionId == option.id;
              final isWrongPick = revealed && isSelected && feedback!.isCorrect == false;
              Color? tint;
              if (isCorrect) tint = Colors.green.withValues(alpha: 0.18);
              if (isWrongPick) tint = Colors.red.withValues(alpha: 0.18);
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Material(
                  color: tint ?? Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
                  borderRadius: BorderRadius.circular(12),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: revealed ? null : () => controller.select(option.id),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 14,
                            backgroundColor: isSelected
                                ? Theme.of(context).colorScheme.primary
                                : Theme.of(context).colorScheme.surface,
                            child: Text(
                              option.label,
                              style: TextStyle(
                                fontSize: 12,
                                color: isSelected ? Theme.of(context).colorScheme.onPrimary : null,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(child: Text(option.text)),
                          if (isCorrect) const Icon(Icons.check_circle, color: Colors.green),
                          if (isWrongPick) const Icon(Icons.cancel, color: Colors.red),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            }),
            if (selected != null && !revealed)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: controller.clearSelection,
                  icon: const Icon(Icons.clear),
                  label: const Text('Clear answer'),
                ),
              ),
            if (revealed && feedback!.explanation.isNotEmpty) ...[
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        feedback.isCorrect == true ? 'Correct!' : 'Correct answer: ${feedback.correctOptionLabel}',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: feedback.isCorrect == true ? Colors.green.shade700 : Colors.red.shade700,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(feedback.explanation),
                    ],
                  ),
                ),
              ),
            ],
            if (controller.error != null) ...[
              const SizedBox(height: 12),
              Text(controller.error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _bookmark(BuildContext context, int questionId) async {
    final messenger = ScaffoldMessenger.of(context);
    await context.read<BookmarkRepository>().add(targetType: 'question', targetId: questionId);
    messenger.showSnackBar(const SnackBar(content: Text('Question bookmarked')));
  }

  void _showPalette(BuildContext context, AttemptController controller) {
    showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Answered ${controller.answeredCount}/${controller.attempt.total} • '
                'marked ${controller.markedCount}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (var index = 0; index < controller.attempt.total; index++)
                    _PaletteChip(
                      index: index,
                      answered: controller.selectedOptions.containsKey(controller.attempt.questions[index].id),
                      marked: controller.markedForReview[controller.attempt.questions[index].id] ?? false,
                      current: controller.index == index,
                      onTap: () {
                        controller.goTo(index);
                        Navigator.of(sheetContext).pop();
                      },
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PaletteChip extends StatelessWidget {
  const _PaletteChip({
    required this.index,
    required this.answered,
    required this.marked,
    required this.current,
    required this.onTap,
  });

  final int index;
  final bool answered;
  final bool marked;
  final bool current;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    Color background = scheme.surfaceContainerHighest;
    if (answered) background = Colors.green.shade600;
    if (marked) background = Colors.purple.shade400;
    return InkWell(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(8),
          border: current ? Border.all(color: scheme.primary, width: 2) : null,
        ),
        child: Text(
          '${index + 1}',
          style: TextStyle(color: answered || marked ? Colors.white : scheme.onSurface),
        ),
      ),
    );
  }
}
