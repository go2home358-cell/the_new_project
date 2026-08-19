import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/api_exception.dart';
import '../data/practice_repository.dart';
import '../models/attempt.dart';

/// Drives one practice session or timed test: navigation, per-question answers,
/// mark-for-review flags, the countdown and submission.
class AttemptController extends ChangeNotifier {
  AttemptController(this._repository, this.attempt) {
    _questionStopwatch.start();
    if (attempt.isTimed) {
      _remainingSeconds = attempt.durationSeconds! - DateTime.now().toUtc().difference(attempt.startedAt.toUtc()).inSeconds;
      _ticker = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
    }
  }

  final PracticeRepository _repository;
  final Attempt attempt;

  final Map<int, int> selectedOptions = {};
  final Map<int, bool> markedForReview = {};
  final Map<int, AnswerFeedback> feedback = {};
  final Stopwatch _questionStopwatch = Stopwatch();

  Timer? _ticker;
  int _remainingSeconds = 0;
  int _index = 0;
  bool _submitting = false;
  bool _expired = false;
  String? error;
  AttemptResult? result;

  int get index => _index;
  int get remainingSeconds => _remainingSeconds < 0 ? 0 : _remainingSeconds;
  bool get submitting => _submitting;
  bool get expired => _expired;
  bool get isPractice => !attempt.isTimed;
  int get answeredCount => selectedOptions.length;
  int get markedCount => markedForReview.values.where((value) => value).length;

  /// Practice sessions reveal the answer as soon as one is picked; timed tests
  /// only reveal it after submission.
  AnswerFeedback? get currentFeedback => feedback[currentQuestionId];
  int get currentQuestionId => attempt.questions[_index].id;

  void goTo(int index) {
    if (index < 0 || index >= attempt.questions.length || index == _index) return;
    _index = index;
    _questionStopwatch
      ..reset()
      ..start();
    notifyListeners();
  }

  void next() => goTo(_index + 1);

  void previous() => goTo(_index - 1);

  Future<void> select(int optionId) async {
    final questionId = currentQuestionId;
    if (feedback[questionId]?.revealsAnswer == true) return; // answered practice question is locked
    selectedOptions[questionId] = optionId;
    notifyListeners();
    await _sync(questionId, optionId);
  }

  Future<void> toggleMarkForReview() async {
    final questionId = currentQuestionId;
    markedForReview[questionId] = !(markedForReview[questionId] ?? false);
    notifyListeners();
    await _sync(questionId, selectedOptions[questionId]);
  }

  Future<void> clearSelection() async {
    final questionId = currentQuestionId;
    if (feedback[questionId]?.revealsAnswer == true) return;
    selectedOptions.remove(questionId);
    notifyListeners();
    await _sync(questionId, null);
  }

  Future<AttemptResult?> submit() async {
    if (_submitting) return result;
    _submitting = true;
    notifyListeners();
    try {
      result = await _repository.submit(attempt.id);
      _ticker?.cancel();
      return result;
    } on ApiException catch (exception) {
      error = exception.message;
      return null;
    } finally {
      _submitting = false;
      notifyListeners();
    }
  }

  Future<void> _sync(int questionId, int? optionId) async {
    try {
      final response = await _repository.answer(
        attemptId: attempt.id,
        questionId: questionId,
        selectedOptionId: optionId,
        markedForReview: markedForReview[questionId] ?? false,
        timeSpentSeconds: _questionStopwatch.elapsed.inSeconds,
      );
      feedback[questionId] = response;
      error = null;
    } on ApiException catch (exception) {
      error = exception.message;
      if (exception.statusCode == 409) _expired = true;
    }
    notifyListeners();
  }

  void _tick() {
    _remainingSeconds -= 1;
    if (_remainingSeconds <= 0) {
      _remainingSeconds = 0;
      _ticker?.cancel();
      _expired = true;
    }
    notifyListeners();
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }
}
