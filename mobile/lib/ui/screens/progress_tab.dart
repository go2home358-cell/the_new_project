import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/formatters.dart';
import '../../data/progress_repository.dart';
import '../../models/progress.dart';
import '../widgets/async_view.dart';
import '../widgets/section_header.dart';
import '../widgets/stat_tile.dart';
import 'practice_launcher.dart';

class ProgressData {
  ProgressData(this.summary, this.subjects, this.weakTopics);

  final ProgressSummary summary;
  final List<ScopePerformance> subjects;
  final List<WeakTopic> weakTopics;
}

class ProgressTab extends StatelessWidget {
  const ProgressTab({super.key});

  Future<ProgressData> _load(ProgressRepository repository) async {
    final results = await Future.wait([
      repository.summary(),
      repository.subjectPerformance(),
      repository.weakTopics(),
    ]);
    return ProgressData(
      results[0] as ProgressSummary,
      results[1] as List<ScopePerformance>,
      results[2] as List<WeakTopic>,
    );
  }

  @override
  Widget build(BuildContext context) {
    final repository = context.read<ProgressRepository>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Progress'),
        actions: [
          IconButton(
            tooltip: 'Badges',
            onPressed: () => context.push('/badges'),
            icon: const Icon(Icons.military_tech_outlined),
          ),
        ],
      ),
      body: AsyncView<ProgressData>(
        load: () => _load(repository),
        builder: (context, data, reload) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.7,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              children: [
                StatTile(label: 'Attempted', value: '${data.summary.questionsAttempted}', icon: Icons.quiz_outlined),
                StatTile(label: 'Accuracy', value: formatPercent(data.summary.accuracy), icon: Icons.track_changes),
                StatTile(
                  label: 'Average score',
                  value: formatPercent(data.summary.averageScore),
                  icon: Icons.stacked_line_chart,
                ),
                StatTile(
                  label: 'Study time',
                  value: formatStudyTime(data.summary.studySeconds),
                  icon: Icons.schedule,
                ),
              ],
            ),
            if (data.subjects.isNotEmpty) ...[
              const SectionHeader(title: 'Accuracy by subject'),
              SizedBox(height: 220, child: _SubjectAccuracyChart(subjects: data.subjects)),
            ],
            const SectionHeader(title: 'Weak topics'),
            if (data.weakTopics.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('No weak topics yet — answer a few more questions to unlock this analysis.'),
                ),
              )
            else
              ...data.weakTopics.map(
                (topic) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Card(
                    child: ListTile(
                      title: Text(topic.topicName),
                      subtitle: Text(
                        '${topic.subjectName} • ${topic.chapterName}\n'
                        '${topic.correct}/${topic.attempted} correct (${formatPercent(topic.accuracy)})',
                      ),
                      isThreeLine: true,
                      trailing: TextButton(
                        onPressed: () => PracticeLauncher.start(context, mode: 'topic', topicId: topic.topicId),
                        child: const Text('Practise'),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SubjectAccuracyChart extends StatelessWidget {
  const _SubjectAccuracyChart({required this.subjects});

  final List<ScopePerformance> subjects;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return BarChart(
      BarChartData(
        maxY: 100,
        borderData: FlBorderData(show: false),
        gridData: const FlGridData(show: true, drawVerticalLine: false),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(),
          rightTitles: const AxisTitles(),
          leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 32, interval: 25)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index < 0 || index >= subjects.length) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    subjects[index].name.split(' ').first,
                    style: const TextStyle(fontSize: 11),
                  ),
                );
              },
            ),
          ),
        ),
        barGroups: [
          for (var index = 0; index < subjects.length; index++)
            BarChartGroupData(
              x: index,
              barRods: [
                BarChartRodData(
                  toY: subjects[index].accuracy,
                  width: 18,
                  color: scheme.primary,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                ),
              ],
            ),
        ],
      ),
    );
  }
}
