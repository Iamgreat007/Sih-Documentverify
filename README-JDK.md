This project includes helper scripts to install and use a project-local OpenJDK 17.

Install local JDK 17 (no admin):

```powershell
# from project root
.\scripts\install-jdk.ps1
```

Run the Spring Boot app using the local JDK:

```powershell
# runs mvnw in facerecognition with JAVA_HOME set to local JDK
.\scripts\run-with-local-jdk.ps1
```

Create a distribution ZIP that includes the local JDK (after packaging):

```powershell
# from repository root
cd facerecognition
..\mvnw.cmd -DskipTests package
# distribution ZIP will be in facerecognition/target named facerecognition-0.0.1-SNAPSHOT-dist.zip
```
