import os

# Database integration tests should provide a disposable PostgreSQL URL.
os.environ.setdefault(
	"DATABASE_URL",
	"postgresql://zenach:zenach_password@127.0.0.1:5433/zenach_test",
)
