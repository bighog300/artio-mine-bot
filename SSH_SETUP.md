# SSH Setup Guide — Passwordless Authentication

**Required for deployment script to work without password prompts**

---

## Quick Check: Do You Need This?

Run this command:
```bash
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

**If it prints `connected`:** ✅ You're all set! Skip this guide.

**If it prompts for password or fails:** ⚠️ Follow this guide.

---

## Setup Instructions (5 minutes)

### Step 1: Generate SSH Key (if you don't have one)

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

When prompted:
- **File location:** Press Enter (use default `~/.ssh/id_ed25519`)
- **Passphrase:** Leave empty (press Enter twice)

```
Generating public/private ed25519 key pair.
Enter file in which to save the key (/home/user/.ssh/id_ed25519): [Press Enter]
Enter passphrase (empty for no passphrase): [Press Enter]
Enter same passphrase again: [Press Enter]
Your identification has been saved in /home/user/.ssh/id_ed25519
Your public key has been saved in /home/user/.ssh/id_ed25519.pub
```

### Step 2: Add Your Public Key to Remote

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub craig@dockerdev
```

You'll be prompted for your password once:
```
/usr/bin/ssh-copy-id: INFO: attempting to log in with key file '/home/user/.ssh/id_ed25519.pub'
craig@dockerdev's password: [Enter password here]
```

After this, the key is installed on the remote.

### Step 3: Verify Passwordless Access

```bash
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

Should print `connected` without any password prompt.

---

## Detailed Explanation

### What is SSH Key-Based Authentication?

Instead of typing your password every time, SSH keys use cryptography:

- **Private Key** (on your computer) — Secret, like a password
- **Public Key** (on remote server) — Shared openly

When you connect, SSH proves you have the private key without sending a password.

**Benefits:**
- ✅ More secure than passwords
- ✅ No password transmitted over network
- ✅ Can't be brute-forced
- ✅ Automation friendly (no password prompts)

### Key Types

- **Ed25519** ← Recommended (what we use above)
  - Modern, secure, small key size
  - Fast, no hardware needed

- **RSA** ← Also fine, older
  - Widely supported
  - Use 4096-bit: `ssh-keygen -t rsa -b 4096`

### File Locations

```
~/.ssh/id_ed25519       ← Your PRIVATE key (keep secret!)
~/.ssh/id_ed25519.pub   ← Your PUBLIC key (safe to share)
```

---

## Troubleshooting

### "Permission denied (publickey)"

**Cause:** Key not properly installed on remote

**Solution:**
```bash
# Verify key is readable
ls -la ~/.ssh/id_ed25519
# Should show: -rw------- (600 permissions)

# Check if key was added to remote
ssh craig@dockerdev 'cat ~/.ssh/authorized_keys | grep ed25519'

# If not there, copy manually:
ssh-copy-id -i ~/.ssh/id_ed25519.pub craig@dockerdev
```

### "ssh-copy-id: command not found"

**Cause:** Tool not installed (rare on macOS/Linux)

**Solution (manual method):**
```bash
# Copy your public key manually
cat ~/.ssh/id_ed25519.pub | ssh craig@dockerdev 'cat >> ~/.ssh/authorized_keys'

# Or if that fails:
# 1. View your public key
cat ~/.ssh/id_ed25519.pub

# 2. SSH to remote (will prompt for password once)
ssh craig@dockerdev

# 3. On remote machine, add your public key
# Paste the output from step 1:
echo "ssh-ed25519 AAAA... your-email@example.com" >> ~/.ssh/authorized_keys

# 4. Fix permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# 5. Exit and test
exit
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

### "No such file or directory" when generating key

**Cause:** .ssh directory doesn't exist

**Solution:**
```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "your-email@example.com"
```

### Still Getting Password Prompt

**Cause:** SSH not using key, SSH agent issue

**Solution:**
```bash
# Check which key SSH is trying
ssh -v craig@dockerdev "echo test" 2>&1 | grep "Offering\|Authentications"

# Start SSH agent (if needed)
eval "$(ssh-agent -s)"

# Add key to agent
ssh-add ~/.ssh/id_ed25519

# Test
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

### "Host key verification failed"

**Cause:** First SSH connection, remote server not yet trusted

**Solution:**
```bash
# This is normal for first connection. Type "yes":
ssh craig@dockerdev
# The authenticity of host 'craig@dockerdev (...)' can't be established.
# Are you sure you want to continue connecting (yes/no/[fingerprint])? yes

# After accepting, subsequent connections won't ask
ssh craig@dockerdev "echo connected"
```

---

## Advanced Configuration (Optional)

### Config File for Easier Access

Create `~/.ssh/config`:

```
Host dockerdev
    HostName dockerdev
    User craig
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new
```

Then use simpler commands:
```bash
ssh dockerdev              # Instead of: ssh craig@dockerdev
scp file dockerdev:~/      # Instead of: scp file craig@dockerdev:~/
```

### Multiple Keys

If you have multiple servers:
```
Host dockerdev
    HostName dockerdev
    User craig
    IdentityFile ~/.ssh/id_ed25519

Host production
    HostName prod.example.com
    User craig
    IdentityFile ~/.ssh/id_rsa
```

### SSH Agent Setup (Keep Credentials in Memory)

```bash
# Add to ~/.bashrc or ~/.zshrc
if [ -z "$SSH_AUTH_SOCK" ]; then
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519 2>/dev/null
fi
```

Then every new terminal session automatically has your key loaded.

---

## Security Best Practices

### ✅ Do

- ✅ Keep private key safe (file permissions 600)
- ✅ Keep .ssh directory secure (permissions 700)
- ✅ Use passphrases for private keys if storing sensitive servers
- ✅ Rotate keys periodically (yearly recommended)
- ✅ Use separate keys for different environments

### ❌ Don't

- ❌ Share private key (id_ed25519)
- ❌ Commit private key to git
- ❌ Use same key on untrusted servers
- ❌ Store key in cloud unencrypted
- ❌ Leave terminal unlocked when key is in SSH agent

### Remove Key from Server (if compromised)

```bash
ssh craig@dockerdev
# Remove the line from ~/.ssh/authorized_keys
nano ~/.ssh/authorized_keys
# Or remove entirely:
rm ~/.ssh/authorized_keys
exit
```

---

## Verification Checklist

After setup, verify everything works:

```bash
# 1. Private key exists and readable
ls -la ~/.ssh/id_ed25519
# Should show: -rw------- (600 permissions)

# 2. Public key exists
ls -la ~/.ssh/id_ed25519.pub
# Should show: -rw-r--r-- (644 permissions)

# 3. Can connect without password
ssh -o BatchMode=yes craig@dockerdev "echo connected"
# Should output: connected

# 4. Can connect with explicit key
ssh -i ~/.ssh/id_ed25519 craig@dockerdev "echo connected"
# Should output: connected

# 5. Verify key on server
ssh craig@dockerdev "cat ~/.ssh/authorized_keys | grep -o 'ed25519' | head -1"
# Should output: ed25519
```

---

## Debugging

If something still doesn't work, debug with verbose output:

```bash
# Show detailed connection info
ssh -vvv craig@dockerdev "echo test"

# Look for these lines to verify key usage:
# - "Offering public key"
# - "Authentications that can continue"
# - "Authentication succeeded"

# If you see "debug1: No more authentication methods to try" 
# → Key not being offered

# If you see "key_load_private: Permission denied"
# → Fix key permissions:
chmod 600 ~/.ssh/id_ed25519
chmod 700 ~/.ssh
```

---

## Summary

After completing this guide:

1. ✅ SSH key generated locally
2. ✅ Public key installed on craig@dockerdev
3. ✅ Can SSH without password prompts
4. ✅ Ready to run deployment script

**Test command:**
```bash
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

If this works, you're ready to deploy! 🚀

---

## If You Still Have Issues

### Option 1: Manually Verify Steps (Linux/macOS Terminal)

```bash
# 1. Check if you have SSH keys
ls ~/.ssh/id_ed25519

# 2. If not, create one
ssh-keygen -t ed25519

# 3. Check if authorized_keys exists on remote
ssh craig@dockerdev 'test -f ~/.ssh/authorized_keys && echo "File exists"'

# 4. If not, create it
ssh craig@dockerdev 'mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'

# 5. Copy your public key
cat ~/.ssh/id_ed25519.pub | ssh craig@dockerdev 'cat >> ~/.ssh/authorized_keys'

# 6. Test
ssh -o BatchMode=yes craig@dockerdev "echo connected"
```

### Option 2: Contact System Administrator

If you've tried everything and it's still not working:
- Provide the output of: `ssh -vvv craig@dockerdev "echo test"` 2>&1
- Ask sys admin to check:
  - Is sshd running?
  - Are permissions correct on /home/craig/.ssh?
  - Are there firewall rules blocking SSH?
  - Is PasswordAuthentication enabled in sshd_config?

---

**You're all set!** Go back to QUICK_START.md to deploy. 🚀
