#include "db_wrap.h"
#include "db_wrap_dbi.h"
#include <assert.h>

#include <stdio.h> /*printf()*/
#include <stdlib.h> /*getenv()*/
#include <string.h> /* strlen() */
#define MARKER printf("MARKER: %s:%d:%s():\t",__FILE__,__LINE__,__func__); printf


static db_wrap_conn_params paramMySql = db_wrap_conn_params_empty_m;
static db_wrap_conn_params paramSqlite = db_wrap_conn_params_empty_m;

void test_mysql_1()
{
	db_wrap * wr = NULL;
	dbi_conn conn = dbi_conn_new("mysql");
	assert(conn);
	int rc = db_wrap_dbi_init(conn, &paramMySql, &wr);
	assert(0 == rc);
	assert(wr);
	rc = wr->api->connect(wr);
	assert(0 == rc);

	char * sqlCP = NULL;
	char const * sql = "hi, 'world'";
	size_t const sz = strlen(sql);
	size_t const sz2 = wr->api->sql_quote(wr, sql, sz, &sqlCP);
	assert(0 != sz2);
	assert(sz != sz2);
	/* ACHTUNG: what libdbi does here with the escaping is NOT SQL STANDARD. */
	assert(0 == strcmp("'hi, \\'world\\''", sqlCP) );
	rc = wr->api->free_string(wr, sqlCP);
	assert(0 == rc);


	rc = wr->api->finalize(wr);
	assert(0 == rc);
}

void test_sqlite_1()
{
	db_wrap * wr = NULL;
	dbi_conn conn = dbi_conn_new("sqlite3");
	assert(conn);
	int rc = db_wrap_dbi_init(conn, &paramSqlite, &wr);
	assert(0 == rc);
	assert(wr);
	char const * dbdir = getenv("PWD");
	rc = wr->api->option_set(wr, "sqlite3_dbdir", dbdir);
	assert(0 == rc);
	rc = wr->api->connect(wr);
	assert(0 == rc);
	char * errmsg = NULL;
	rc = wr->api->error_message(wr, &errmsg, NULL);
	assert(0 == rc);
	assert(NULL == errmsg);

	char * sqlCP = NULL;
	char const * sql = "hi, 'world'";
	size_t const sz = strlen(sql);
	size_t const sz2 = wr->api->sql_quote(wr, sql, sz, &sqlCP);
	assert(0 != sz2);
	assert(sz != sz2);
	assert(0 == strcmp("'hi, ''world'''", sqlCP) );
	rc = wr->api->free_string(wr, sqlCP);
	assert(0 == rc);

	sql = NULL;
	rc = wr->api->option_get(wr, "sqlite3_dbdir", &sql);
	assert(0 == rc);
	assert(0 == strcmp( sql, dbdir) );

	rc = wr->api->finalize(wr);
	assert(0 == rc);
}

int main(int argc, char const ** argv)
{
	{
		paramMySql.host = "localhost";
		paramMySql.port = 3306;
		paramMySql.username = "merlin";
		paramMySql.password = "merlin";
		paramMySql.dbname = "merlin";
	}
	{
		paramSqlite.dbname = "merlin.sqlite";
	}
	dbi_initialize(NULL);
	test_mysql_1();
	test_sqlite_1();
	dbi_shutdown();
	MARKER("If you got this far, it worked.\n");
	return 0;
}