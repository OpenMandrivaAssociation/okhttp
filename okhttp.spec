Name:		okhttp
Version:	4.12.0
Release:	1
Summary:	HTTP client for Java and Kotlin
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/square/okhttp
# Square tag parent-4.12.0. The JVM sources are compiled with kotlinc.
# Android, Conscrypt, BouncyCastle JSSE, and OpenJSSE are compileOnly
# platform adapters. Cooker has none of those jars. On a normal JDK the
# client selects Jdk9Platform, so those sources are left out of the jar.
# animal-sniffer-annotations is retention CLASS and is not a runtime dependency.
Source0:	okhttp-%{version}.tar.gz
Patch0:		okhttp-jdk-platform.patch

BuildArch:	noarch
BuildRequires:	java-21-openjdk-devel
BuildRequires:	kotlin
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib)
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib-jdk7)
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib-jdk8)
BuildRequires:	mvn(com.squareup.okio:okio)
BuildRequires:	mvn(org.codehaus.mojo:animal-sniffer-annotations)

%description
com.squareup.okhttp3:okhttp %{version}. HTTP and HTTP/2 client.
The JVM sources are compiled with the installed kotlinc against okio.

%prep
%autosetup -n okhttp-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
rm -f okhttp/src/main/kotlin/okhttp3/internal/platform/Android10Platform.kt
rm -f okhttp/src/main/kotlin/okhttp3/internal/platform/AndroidPlatform.kt
rm -f okhttp/src/main/kotlin/okhttp3/internal/platform/BouncyCastlePlatform.kt
rm -f okhttp/src/main/kotlin/okhttp3/internal/platform/ConscryptPlatform.kt
rm -f okhttp/src/main/kotlin/okhttp3/internal/platform/OpenJSSEPlatform.kt
rm -rf okhttp/src/main/kotlin/okhttp3/internal/platform/android
sed 's/$projectVersion/%{version}/' okhttp/src/main/java-templates/okhttp3/OkHttp.kt > okhttp/src/main/kotlin/okhttp3/OkHttp.kt
grep -F -q 'const val VERSION = "%{version}"' okhttp/src/main/kotlin/okhttp3/OkHttp.kt
if grep -F -q '$projectVersion' okhttp/src/main/kotlin/okhttp3/OkHttp.kt; then
	exit 1
fi
if grep -F -e ConscryptPlatform -e Android10Platform -e OpenJSSEPlatform -e BouncyCastlePlatform -e AndroidLog okhttp/src/main/kotlin/okhttp3/internal/platform/Platform.kt; then
	exit 1
fi
test "$(find okhttp/src/main/kotlin -name '*.kt' | wc -l)" -eq 108

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
CPSTD=%{_javadir}/kotlin-stdlib.jar
CPJDK7=%{_javadir}/kotlin-stdlib-jdk7.jar
CPJDK8=%{_javadir}/kotlin-stdlib-jdk8.jar
CPOKIO=%{_javadir}/okio.jar
CPANN=%{_javadir}/animal-sniffer-annotations.jar
test -s "$CPSTD"
test -s "$CPJDK7"
test -s "$CPJDK8"
test -s "$CPOKIO"
test -s "$CPANN"
find okhttp/src/main/kotlin -name '*.kt' > kt.list
test "$(wc -l < kt.list)" -eq 108
mkdir -p classes
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 1.8 \
	-cp "$CPSTD:$CPJDK7:$CPJDK8:$CPOKIO:$CPANN" \
	-d classes @kt.list
test -s classes/okhttp3/OkHttpClient.class
test -s classes/okhttp3/Request.class
test -s classes/okhttp3/OkHttp.class
test -s classes/okhttp3/internal/platform/Jdk9Platform.class
if find classes -name '*.class' | grep -E '/Android|/Conscrypt|/BouncyCastle|/OpenJSSE|/android/'; then
	exit 1
fi
test "$(find classes -name '*.class' | wc -l)" -eq 281
javap -v -classpath classes okhttp3.OkHttpClient | grep -F -q 'major version: 52'
cp -a okhttp/src/main/resources/. classes/
test -s classes/okhttp3/internal/publicsuffix/publicsuffixes.gz
printf '%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: okhttp3' "Implementation-Version: %{version}" > manifest.mf
jar cfm okhttp.jar manifest.mf -C classes .
jar i okhttp.jar
desc=$(jar --describe-module --file okhttp.jar)
printf '%s\n' "$desc"
printf '%s\n' "$desc" | grep -F -q ' okhttp3'
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	exit 1
fi

cat > okhttp.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.squareup.okhttp3</groupId>
  <artifactId>okhttp</artifactId>
  <version>%{version}</version>
  <name>okhttp</name>
  <description>An HTTP client for Android, Kotlin, and Java.</description>
  <url>https://github.com/square/okhttp</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>com.squareup.okio</groupId>
      <artifactId>okio</artifactId>
      <version>3.6.0</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
      <version>2.0.21</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact okhttp.pom:okhttp.jar \
	--file-name okhttp \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/com.squareup.okhttp3/okhttp.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "okhttp"' "$idx"
test -s %{buildroot}%{_javadir}/okhttp.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/okhttp.jar
test -s "$JAR"
STDLIB=%{_javadir}/kotlin-stdlib.jar:%{_javadir}/kotlin-stdlib-jdk7.jar:%{_javadir}/kotlin-stdlib-jdk8.jar
OKIO=%{_javadir}/okio.jar
mkdir -p check
cat > check/Check.java << 'EOF'
import okhttp3.OkHttp;
import okhttp3.OkHttpClient;
import okhttp3.Request;
public class Check {
	public static void main(String[] args) {
		OkHttpClient client = new OkHttpClient();
		Request req = new Request.Builder().url("https://example.com/").build();
		if (!"%{version}".equals(OkHttp.VERSION)) {
			throw new RuntimeException(OkHttp.VERSION);
		}
		if (!"GET".equals(req.method())) {
			throw new RuntimeException(req.method());
		}
		if (client.protocols().size() != 2) {
			throw new RuntimeException(Integer.toString(client.protocols().size()));
		}
		System.out.println("okhttp_ok " + OkHttp.VERSION + " " + req.method() + " " + client.protocols().size());
	}
}
EOF
javac --release 8 -encoding UTF-8 -Xlint:-options -cp "$JAR:$OKIO:$STDLIB" -d check check/Check.java
java -cp "check:$JAR:$OKIO:$STDLIB" Check > check/out.txt
cat check/out.txt
grep -F -qx 'okhttp_ok %{version} GET 2' check/out.txt

%files -f .mfiles
%license LICENSE.txt
