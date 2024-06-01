
package com.example.fn;

import com.fnproject.fn.api.RuntimeContext;
import java.sql.*;
import com.fasterxml.jackson.databind.*;
import java.io.*;
import java.util.*;

public class HelloFunction {
    
    public HelloFunction() throws Exception {
    }

    public String handleRequest(String input) {
        String json = "-";
        try {        
            Class.forName("org.postgresql.Driver");        
            List<Dept> rows = new ArrayList<Dept>();
            
            try {
                Connection conn = DriverManager.getConnection( System.getenv("JDBC_URL") , System.getenv("DB_USER"), System.getenv("DB_PASSWORD"));
                Statement stmt = conn.createStatement();
                ResultSet rs = stmt.executeQuery("SELECT deptno, dname, loc FROM dept");
                while (rs.next()) {
                    rows.add(new Dept(rs.getInt(1), rs.getString(2), rs.getString(3) ));
                }
                rs.close();
                stmt.close();
                conn.close();
            } catch (SQLException e) {
                System.err.println(e.getMessage());
                e.printStackTrace();
            }
            // Jackson 
            ObjectMapper objectMapper = new ObjectMapper();
            json = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(rows);
        } catch (Exception e) {
            System.err.println("Exception:" + e.getMessage());
            e.printStackTrace();
        }
        return json;
    }
}