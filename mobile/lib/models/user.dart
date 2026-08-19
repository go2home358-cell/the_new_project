class AppUser {
  AppUser({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    required this.xp,
    required this.level,
    required this.streakCount,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as int,
        name: json['name'] as String,
        email: json['email'] as String,
        role: json['role'] as String,
        xp: json['xp'] as int? ?? 0,
        level: json['level'] as int? ?? 1,
        streakCount: json['streak_count'] as int? ?? 0,
      );

  final int id;
  final String name;
  final String email;
  final String role;
  final int xp;
  final int level;
  final int streakCount;

  bool get isAdmin => role == 'admin';
}
