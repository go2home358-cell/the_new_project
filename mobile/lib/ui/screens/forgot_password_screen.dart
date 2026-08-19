import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../state/auth_controller.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _email = TextEditingController();
  final _token = TextEditingController();
  final _password = TextEditingController();
  bool _requested = false;

  @override
  void dispose() {
    _email.dispose();
    _token.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _request() async {
    final auth = context.read<AuthController>();
    final token = await auth.forgotPassword(_email.text.trim());
    if (!mounted) return;
    setState(() {
      _requested = true;
      if (token != null) _token.text = token;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          token == null
              ? 'If the email exists, a reset link has been sent.'
              : 'Development mode: reset token filled in for you.',
        ),
      ),
    );
  }

  Future<void> _reset() async {
    final auth = context.read<AuthController>();
    final ok = await auth.resetPassword(token: _token.text.trim(), newPassword: _password.text);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? 'Password updated. Please log in.' : auth.error ?? 'Reset failed')),
    );
    if (ok) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    return Scaffold(
      appBar: AppBar(title: const Text('Reset password')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline)),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: auth.busy ? null : _request,
                    child: const Text('Send reset token'),
                  ),
                  if (_requested) ...[
                    const Divider(height: 40),
                    TextField(
                      controller: _token,
                      decoration: const InputDecoration(labelText: 'Reset token', prefixIcon: Icon(Icons.key)),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _password,
                      obscureText: true,
                      decoration: const InputDecoration(
                        labelText: 'New password (min 8 characters)',
                        prefixIcon: Icon(Icons.lock_outline),
                      ),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: auth.busy ? null : _reset,
                      child: const Text('Set new password'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
