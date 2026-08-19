/// Runtime configuration.
///
/// The API base URL is supplied at build time so no environment specific value
/// is baked into the source:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
}
