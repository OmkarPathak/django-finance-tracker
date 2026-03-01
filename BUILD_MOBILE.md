# Building the Mobile App (iOS)

Since this project uses **Capacitor** to wrap the Django web application, the build process for iOS involves a few steps to sync your code and then use Xcode for the final build.

## Prerequisites

- **macOS** with the latest version of **Xcode** installed.
- **Node.js** and **npm** installed.
- **CocoaPods** installed (`sudo gem install cocoapods`).

## Build Steps

### 1. Prepare the Django Web App
Ensure your Django application is running and accessible. The Capacitor app is configured to load the URL specified in `mobile/capacitor.config.json` (currently `https://trackmyrupee.com`).

### 2. Sync Capacitor
Navigate to the `mobile` directory and sync the Capacitor bridge. This ensures all plugins and configurations are correctly copied to the iOS project.

```bash
cd mobile
npm install
npm run ios:sync
```

### 3. Open in Xcode
You can open the iOS project directly in Xcode using the helper script:

```bash
npm run ios:open
```

Alternatively, open `mobile/ios/App/App.xcworkspace` in Xcode manually.

### 4. Build and Archive in Xcode
Once Xcode is open:

1.  **Select Target**: Select the **App** target and a destination (either a physical device or "Any iOS Device (arm64)").
2.  **Signing & Capabilities**: Ensure you have a valid Development Team selected under the **Signing & Capabilities** tab.
3.  **Build**: Press `Cmd + B` to build the project.
4.  **Archive**: To create a build for distribution (App Store or TestFlight), go to **Product > Archive**.
5.  **Distribute**: Once the archive is complete, the Organizer window will open. Click **Distribute App** and follow the prompts.

## Troubleshooting

### Troubleshooting Signing (Personal Team)

If you see a "Communication with Apple failed" error in Xcode's Signing & Capabilities tab even after connecting your device:

1.  **Select the Correct Run Destination**: In the top bar of Xcode (next to the Play button), click the device name and ensure your physical iPhone is explicitly selected under the "iOS Devices" section. Xcode won't provision the device unless it's the active target.
2.  **Change the Bundle Identifier**: This is a very common fix. `com.trackmyrupee.app` might be restricted or already partially registered.
    - Go to the **General** tab in Xcode.
    - Change **Bundle Identifier** to something unique, like `com.yourname.trackmyrupee` or `com.tmr.finance.[random-string]`.
    - Try clicking **Try Again** after changing it.
3.  **Check Apple Account**:
    - Go to **Xcode > Settings (or Preferences) > Accounts**.
    - Ensure your Apple ID is logged in.
    - Select your ID and click **Manage Certificates...** to ensure a "Development" certificate exists.
4.  **VPN/Network Check**: Ensure you are not on a VPN, as it often blocks communication with Apple's signing servers.
5.  **Restart Xcode**: Sometimes Xcode doesn't refresh the device status properly. Close Xcode, unplug your device, plug it back in, and reopen the project.

### CocoaPods Issues
If you see errors related to `Podfile`, run:
```bash
cd mobile/ios/App
pod install
```

## Free vs. Paid Development

The ₹8,700/year cost is for the **Apple Developer Program**, which is only required if you want to:
- Publish your app to the **App Store**.
- Use **TestFlight** for beta testing.
- Use advanced services like iCloud, Apple Pay, or Push Notifications.

### Free Development (Personal Team)
You can develop and test on your own iPhone for **FREE** using a regular Apple ID:
1.  **Xcode > Settings > Accounts**: Add your regular Apple ID.
2.  **Signing & Capabilities**: Select your "Personal Team" name.
3.  **Limitations**:
    - App expires on your phone after **7 days** (you just need to re-run it from Xcode to renew).
    - Limit of **3 active apps** per device.
    - No App Store distribution.

### Verifying the App on Your iPhone

When you first install the app using a free "Personal Team" account, iOS will prevent it from opening with an "Untrusted Developer" error.

**To verify the app:**
1.  On your iPhone, open **Settings**.
2.  Go to **General** > **VPN & Device Management** (or **Profiles & Device Management** on older versions).
3.  Under "Developer App", tap on your **Apple ID**.
4.  Tap **Trust "[Your Apple ID]"**.
#### Trust/Verify Nothing Happens?

If you tap **Trust** or **Verify** and nothing happens (or it just spins), try these steps:

1.  **Internet Connection**: Ensure your iPhone has a stable Wi-Fi or Cellular connection. iOS needs to contact `ppq.apple.com` to verify the certificate.
2.  **Turn off VPN/AdBlock**: If you have a VPN, AdGuard, or any custom DNS active on your iPhone, turn it off temporarily. These often block Apple's verification servers.
3.  **Set Date & Time to Automatic**: Go to **Settings** > **General** > **Date & Time** and ensure **Set Automatically** is enabled.
4.  **Re-install Strategy**:
    - Delete the app from your iPhone.
    - Restart your iPhone.
    - Restart Xcode.
    - Run the app from Xcode again.
5.  **Check for iOS Update**: Sometimes a pending iOS update can interfere with the verification system.
